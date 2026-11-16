package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

type publisher struct {
	URL           string `json:"URL"`
	TargetPort    int    `json:"TargetPort"`
	PublishedPort int    `json:"PublishedPort"`
	Protocol      string `json:"Protocol"`
}

type container struct {
	Name       string      `json:"Name"`
	Service    string      `json:"Service"`
	Image      string      `json:"Image"`
	State      string      `json:"State"`
	Status     string      `json:"Status"`
	CreatedAt  string      `json:"CreatedAt"`
	RunningFor string      `json:"RunningFor"`
	Publishers []publisher `json:"Publishers"`
}

const (
	reset = "\033[0m"
	cyan  = "\033[96m"
	bold  = "\033[1m"
	green = "\033[32m"
	yellow = "\033[33m"
	red   = "\033[31m"
	dim   = "\033[2m"
)

func colorEnabled() bool {
	return termOutput() && os.Getenv("NO_COLOR") == "" && os.Getenv("TERM") != "dumb"
}

func termOutput() bool {
	info, err := os.Stdout.Stat()
	return err == nil && (info.Mode()&os.ModeCharDevice) != 0
}

func paint(s, style string, enabled bool) string {
	if !enabled { return s }
	return style + s + reset
}

var ansiPattern = regexp.MustCompile("\\x1b\\[[0-9;]*m")

func visibleLen(s string) int { return utf8.RuneCountInString(ansiPattern.ReplaceAllString(s, "")) }

func loadContainers(r io.Reader) ([]container, error) {
	data, err := io.ReadAll(r)
	if err != nil { return nil, err }
	data = []byte(strings.TrimSpace(string(data)))
	if len(data) == 0 { return nil, nil }

	var list []container
	if err := json.Unmarshal(data, &list); err == nil { return list, nil }

	var single container
	if err := json.Unmarshal(data, &single); err == nil && (single.Name != "" || single.Service != "") {
		return []container{single}, nil
	}

	// Docker Compose versions may emit one JSON object per line.
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	scanner.Buffer(make([]byte, 4096), 4*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" { continue }
		var item container
		if err := json.Unmarshal([]byte(line), &item); err != nil { return nil, err }
		list = append(list, item)
	}
	return list, scanner.Err()
}

func statusColor(state string) string {
	s := strings.ToLower(state)
	switch {
	case strings.Contains(s, "running") || strings.HasPrefix(s, "up"):
		return green
	case strings.Contains(s, "exited") || strings.Contains(s, "dead") || strings.Contains(s, "removing"):
		return red
	default:
		return yellow
	}
}

func ports(items []publisher) string {
	if len(items) == 0 {
		return "None"
	}

	// Sort by host/protocol and then by published/target port so only
	// genuinely consecutive mappings are combined into ranges.
	sorted := append([]publisher(nil), items...)
	sort.Slice(sorted, func(i, j int) bool {
		a, b := sorted[i], sorted[j]
		if a.URL != b.URL { return a.URL < b.URL }
		if a.Protocol != b.Protocol { return a.Protocol < b.Protocol }
		if a.PublishedPort != b.PublishedPort { return a.PublishedPort < b.PublishedPort }
		return a.TargetPort < b.TargetPort
	})

	type portRange struct {
		host, protocol string
		publishedStart, publishedEnd int
		targetStart, targetEnd int
		published bool
	}
	ranges := make([]portRange, 0, len(sorted))

	for _, item := range sorted {
		proto := item.Protocol
		if proto == "" { proto = "tcp" }
		host := item.URL
		if host == "" { host = "0.0.0.0" }

		current := portRange{
			host: host,
			protocol: proto,
			publishedStart: item.PublishedPort,
			publishedEnd: item.PublishedPort,
			targetStart: item.TargetPort,
			targetEnd: item.TargetPort,
			published: item.PublishedPort > 0,
		}

		if len(ranges) > 0 {
			last := &ranges[len(ranges)-1]
			consecutive := current.published &&
				last.published &&
				current.host == last.host &&
				current.protocol == last.protocol &&
				current.publishedStart == last.publishedEnd+1 &&
				current.targetStart == last.targetEnd+1
			if consecutive {
				last.publishedEnd = current.publishedEnd
				last.targetEnd = current.targetEnd
				continue
			}
		}
		ranges = append(ranges, current)
	}

	formatted := make([]string, 0, len(ranges))
	for _, item := range ranges {
		var mapping string
		if !item.published {
			mapping = fmt.Sprintf("%d/%s", item.targetStart, item.protocol)
		} else if item.publishedStart == item.publishedEnd {
			mapping = fmt.Sprintf("%s:%d->%d/%s", item.host, item.publishedStart, item.targetStart, item.protocol)
		} else {
			mapping = fmt.Sprintf("%s:%d-%d->%d-%d/%s",
				item.host, item.publishedStart, item.publishedEnd,
				item.targetStart, item.targetEnd, item.protocol)
		}
		formatted = append(formatted, mapping)
	}
	return strings.Join(formatted, ",  ")
}

func wrapPortLine(label, value string, maxWidth int) []string {
	prefix := "  " + label
	continuation := strings.Repeat(" ", visibleLen(prefix))
	available := maxWidth - visibleLen(prefix)
	if available < 1 {
		return []string{prefix + value}
	}

	entries := strings.Split(value, ",  ")
	lines := make([]string, 0, 2)
	current := prefix
	currentWidth := visibleLen(prefix)

	for _, entry := range entries {
		separator := ""
		if currentWidth > visibleLen(prefix) {
			separator = ",  "
		}
		entryWidth := visibleLen(entry)
		if currentWidth-visibleLen(prefix)+visibleLen(separator)+entryWidth > maxWidth-visibleLen(prefix) &&
			currentWidth > visibleLen(prefix) {
			lines = append(lines, current)
			current = continuation + entry
			currentWidth = visibleLen(continuation) + entryWidth
			continue
		}
		current += separator + entry
		currentWidth += visibleLen(separator) + entryWidth
	}
	if current != "" {
		lines = append(lines, current)
	}
	return lines
}

func render(items []container) string {
	color := colorEnabled()
	width := 86
	if n, err := strconv.Atoi(os.Getenv("COLUMNS")); err == nil && n >= 60 && n <= 140 { width = n }
	inner := width - 4
	borderWidth := inner + 2
	title := " DevNaro status "
	side := (borderWidth - visibleLen(title)) / 2
	top := paint("╭"+strings.Repeat("─", side), cyan, color) +
		paint(title, bold+cyan, color) +
		paint(strings.Repeat("─", borderWidth-side-visibleLen(title))+"╮", cyan, color)
	bottom := paint("╰"+strings.Repeat("─", borderWidth)+"╯", cyan, color)
	lines := []string{top}

	body := make([]string, 0)
	if len(items) == 0 {
		body = append(body, paint("No container found. Start it with: devnaro start", yellow, color))
	}
	for i, item := range items {
		name := item.Name
		if name == "" { name = item.Service }
		if name == "" { name = "devnaro" }
		service := item.Service
		if service == "" { service = "devnaro" }
		state := item.Status
		if state == "" { state = item.State }
		if state == "" { state = "Unknown" }
		created := item.RunningFor
		if created == "" { created = item.CreatedAt }
		if created == "" { created = "Unknown" }
		body = append(body,
			paint(strings.ToUpper(name), bold+cyan, color),
			fmt.Sprintf("  %s %s", paint(fmt.Sprintf("%-10s", "Service"), cyan, color), service),
			fmt.Sprintf("  %s %s", paint(fmt.Sprintf("%-10s", "Image"), cyan, color), item.Image),
			fmt.Sprintf("  %s %s", paint(fmt.Sprintf("%-10s", "Status"), cyan, color), paint(state, statusColor(state), color)),
			fmt.Sprintf("  %s %s", paint(fmt.Sprintf("%-10s", "Created"), cyan, color), created),
		)
		portLabel := paint(fmt.Sprintf("%-10s", "Ports"), cyan, color)
		body = append(body, wrapPortLine(portLabel, ports(item.Publishers), inner-2)... )
		if i < len(items)-1 { body = append(body, "") }
	}

	for _, line := range body {
		length := visibleLen(line)
		padding := inner - length
		if padding < 0 { padding = 0 }
		lines = append(lines, paint("│", cyan, color)+" "+line+strings.Repeat(" ", padding)+" "+paint("│", cyan, color))
	}
	lines = append(lines, bottom)
	return strings.Join(lines, "\n")
}

func main() {
	items, err := loadContainers(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Unable to read Docker Compose status:", err)
		os.Exit(1)
	}
	fmt.Println(render(items))
}
