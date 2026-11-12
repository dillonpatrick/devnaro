package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
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

func visibleLen(s string) int { return utf8.RuneCountInString(s) }

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
	if len(items) == 0 { return "None" }
	values := make([]string, 0, len(items))
	for _, p := range items {
		proto := p.Protocol
		if proto == "" { proto = "tcp" }
		host := p.URL
		if host == "" { host = "0.0.0.0" }
		if p.PublishedPort > 0 {
			values = append(values, fmt.Sprintf("%s:%d->%d/%s", host, p.PublishedPort, p.TargetPort, proto))
		} else {
			values = append(values, fmt.Sprintf("%d/%s", p.TargetPort, proto))
		}
	}
	sort.Strings(values)
	return strings.Join(values, ",  ")
}

func render(items []container) string {
	color := colorEnabled()
	width := 86
	if n, err := strconv.Atoi(os.Getenv("COLUMNS")); err == nil && n >= 60 && n <= 140 { width = n }
	inner := width - 4
	borderWidth := inner + 2
	title := " DevBox status "
	side := (borderWidth - visibleLen(title)) / 2
	top := paint("╭"+strings.Repeat("─", side), cyan, color) +
		paint(title, bold+cyan, color) +
		paint(strings.Repeat("─", borderWidth-side-visibleLen(title))+"╮", cyan, color)
	bottom := paint("╰"+strings.Repeat("─", borderWidth)+"╯", cyan, color)
	lines := []string{top}

	body := make([]string, 0)
	if len(items) == 0 {
		body = append(body, paint("No container found. Start it with: devbox start", yellow, color))
	}
	for i, item := range items {
		name := item.Name
		if name == "" { name = item.Service }
		if name == "" { name = "devbox" }
		service := item.Service
		if service == "" { service = "devbox" }
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
			fmt.Sprintf("  %s %s", paint(fmt.Sprintf("%-10s", "Ports"), cyan, color), ports(item.Publishers)),
		)
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
