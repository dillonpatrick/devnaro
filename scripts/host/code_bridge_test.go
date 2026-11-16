package main

import "testing"

func TestRemoteFolderURI(t *testing.T) {
	got := remoteFolderURI("devnaro", "/workspace/project")
	want := "vscode-remote://attached-container+6465766e61726f/workspace/project"
	if got != want {
		t.Fatalf("remoteFolderURI() = %q, want %q", got, want)
	}
}
