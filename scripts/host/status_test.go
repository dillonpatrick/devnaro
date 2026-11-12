package main

import (
	"strings"
	"testing"
)

func TestLoadContainersJSONArray(t *testing.T) {
	got, err := loadContainers(strings.NewReader(`[{"Name":"devbox","Service":"devbox","State":"running"}]`))
	if err != nil { t.Fatal(err) }
	if len(got) != 1 || got[0].Name != "devbox" { t.Fatalf("unexpected containers: %#v", got) }
}

func TestLoadContainersNewlineDelimited(t *testing.T) {
	got, err := loadContainers(strings.NewReader("{\"Name\":\"one\"}\n{\"Name\":\"two\"}\n"))
	if err != nil { t.Fatal(err) }
	if len(got) != 2 { t.Fatalf("expected 2 containers, got %d", len(got)) }
}

func TestLoadContainersEmpty(t *testing.T) {
	got, err := loadContainers(strings.NewReader("  \n"))
	if err != nil { t.Fatal(err) }
	if len(got) != 0 { t.Fatalf("expected no containers, got %d", len(got)) }
}

func TestFormatPorts(t *testing.T) {
	got := ports([]publisher{{URL:"127.0.0.1", PublishedPort:8080, TargetPort:80, Protocol:"tcp"}})
	if got != "127.0.0.1:8080->80/tcp" { t.Fatalf("unexpected ports: %s", got) }
}

func TestRenderEmptyState(t *testing.T) {
	got := render(nil)
	for _, expected := range []string{"DevBox status", "No container found", "devbox start"} {
		if !strings.Contains(got, expected) { t.Errorf("rendered output missing %q", expected) }
	}
}
