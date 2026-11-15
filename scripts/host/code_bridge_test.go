package main

import "testing"

func TestRemoteFolderURI(t *testing.T) {
	got := remoteFolderURI("devbox", "/workspace/project")
	want := "vscode-remote://attached-container+646576626f78/workspace/project"
	if got != want {
		t.Fatalf("remoteFolderURI() = %q, want %q", got, want)
	}
}
