package main

import (
    "strings"
    "testing"
)

func TestLoadContainersJSONArray(t *testing.T) {
    got, err := loadContainers(strings.NewReader(`[ {"Name":"devbox","Service":"devbox","State":"running"} ]`))
    if err != nil { t.Fatal(err) }
    if len(got) != 1 || got[0].Name != "devbox" { t.Fatalf("unexpected containers: %#v", got) }
}

func TestLoadContainersNewlineDelimited(t *testing.T) {
    input := `{"Name":"one"}` + "\n" + `{"Name":"two"}` + "\n"
    got, err := loadContainers(strings.NewReader(input))
    if err != nil { t.Fatal(err) }
    if len(got) != 2 { t.Fatalf("expected 2 containers, got %d", len(got)) }
}

func TestLoadContainersEmpty(t *testing.T) {
    got, err := loadContainers(strings.NewReader("  \n"))
    if err != nil { t.Fatal(err) }
    if len(got) != 0 { t.Fatalf("expected no containers, got %d", len(got)) }
}

func TestFormatPorts(t *testing.T) {
    got := ports([]publisher{{URL: "127.0.0.1", PublishedPort: 8080, TargetPort: 80, Protocol: "tcp"}})
    if got != "127.0.0.1:8080->80/tcp" { t.Fatalf("unexpected ports: %s", got) }
}

func TestFormatPortsGroupsConsecutiveMappings(t *testing.T) {
    got := ports([]publisher{
        {URL: "127.0.0.1", PublishedPort: 3002, TargetPort: 3002, Protocol: "tcp"},
        {URL: "127.0.0.1", PublishedPort: 3000, TargetPort: 3000, Protocol: "tcp"},
        {URL: "127.0.0.1", PublishedPort: 3001, TargetPort: 3001, Protocol: "tcp"},
        {URL: "127.0.0.1", PublishedPort: 4173, TargetPort: 4173, Protocol: "tcp"},
    })
    expected := "127.0.0.1:3000-3002->3000-3002/tcp,  127.0.0.1:4173->4173/tcp"
    if got != expected { t.Fatalf("unexpected grouped ports: %s", got) }
}

func TestFormatPortsDoesNotGroupNonConsecutiveMappings(t *testing.T) {
    got := ports([]publisher{
        {URL: "127.0.0.1", PublishedPort: 3000, TargetPort: 3000, Protocol: "tcp"},
        {URL: "127.0.0.1", PublishedPort: 3002, TargetPort: 3002, Protocol: "tcp"},
    })
    expected := "127.0.0.1:3000->3000/tcp,  127.0.0.1:3002->3002/tcp"
    if got != expected { t.Fatalf("unexpected port mappings: %s", got) }
}

func TestWrapPortLineStaysWithinPanelWidth(t *testing.T) {
    value := "127.0.0.1:3000-3010->3000-3010/tcp,  127.0.0.1:4173->4173/tcp,  127.0.0.1:5000-5010->5000-5010/tcp"
    lines := wrapPortLine("Ports     ", value, 78)
    for _, line := range lines {
        if visibleLen(line) > 78 {
            t.Errorf("line exceeds panel width: %d > 78: %q", visibleLen(line), line)
        }
    }
    if len(lines) < 2 {
        t.Fatalf("expected long port list to wrap, got %d line(s)", len(lines))
    }
}

func TestRenderEmptyState(t *testing.T) {
    got := render(nil)
    for _, expected := range []string{"DevBox status", "No container found", "devbox start"} {
        if !strings.Contains(got, expected) { t.Errorf("rendered output missing %q", expected) }
    }
}
