package main

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"net"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
)

type request struct {
	Path string `json:"path"`
}

type response struct {
	OK    bool   `json:"ok"`
	Error string `json:"error,omitempty"`
}

type bridge struct {
	workspace      string
	terminalScript string
}

func (b bridge) handle(conn net.Conn) {
	defer conn.Close()
	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 4096), 1024*1024)
	result := response{OK: false}
	if !scanner.Scan() {
		result.Error = "Empty request."
	} else {
		var req request
		if err := json.Unmarshal(scanner.Bytes(), &req); err != nil {
			result.Error = fmt.Sprintf("Invalid request: %v", err)
		} else if err := b.open(req.Path); err != nil {
			result.Error = err.Error()
		} else {
			result.OK = true
		}
	}
	_ = json.NewEncoder(conn).Encode(result)
}

func (b bridge) open(containerPath string) error {
	cleanPath := filepath.Clean(containerPath)
	if !filepath.IsAbs(cleanPath) || (cleanPath != "/workspace" && !strings.HasPrefix(cleanPath, "/workspace/")) {
		return errors.New("Only paths inside /workspace can be opened.")
	}

	relative := strings.TrimPrefix(strings.TrimPrefix(cleanPath, "/workspace"), string(filepath.Separator))
	target, err := filepath.EvalSymlinks(filepath.Join(b.workspace, relative))
	if err != nil {
		return fmt.Errorf("Path does not exist: %s", containerPath)
	}
	rel, err := filepath.Rel(b.workspace, target)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return errors.New("The requested path resolves outside the workspace.")
	}

	info, err := os.Stat(target)
	if err != nil {
		return fmt.Errorf("Path does not exist: %s", containerPath)
	}
	folder := target
	if !info.IsDir() {
		folder = filepath.Dir(target)
	}
	folderRel, err := filepath.Rel(b.workspace, folder)
	if err != nil {
		return err
	}
	containerFolder := filepath.ToSlash(filepath.Join("/workspace", folderRel))

	vscode, err := exec.LookPath("code")
	if err != nil {
		return errors.New("VS Code CLI 'code' was not found on the host PATH. Install VS Code and make its 'code' command available.")
	}

	cacheHome := os.Getenv("XDG_CACHE_HOME")
	if cacheHome == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return err
		}
		cacheHome = filepath.Join(home, ".cache")
	}
	cacheRoot := filepath.Join(cacheHome, "devbox", "vscode-workspaces")
	if err := os.MkdirAll(cacheRoot, 0700); err != nil {
		return err
	}
	sum := sha256.Sum256([]byte(folder))
	workspaceFile := filepath.Join(cacheRoot, hex.EncodeToString(sum[:])[:16]+".code-workspace")
	config := map[string]any{
		"folders": []map[string]string{{"path": folder}},
		"settings": map[string]any{
			"terminal.integrated.profiles.linux": map[string]any{
				"DevBox": map[string]any{
					"path": "/bin/bash",
					"args": []string{b.terminalScript, containerFolder},
					"icon": "terminal-linux",
				},
			},
			"terminal.integrated.defaultProfile.linux": "DevBox",
		},
	}
	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(workspaceFile, append(data, '\n'), 0600); err != nil {
		return err
	}

	cmd := exec.Command(vscode, "--reuse-window", workspaceFile)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = nil, nil, nil
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("Unable to start VS Code: %v", err)
	}
	_ = cmd.Process.Release()
	return nil
}

func main() {
	socketPath := flag.String("socket", "", "Unix socket path")
	workspacePath := flag.String("workspace", "", "Host workspace path")
	terminalScript := flag.String("terminal-script", "", "Host VS Code terminal launcher")
	flag.Parse()
	if *socketPath == "" || *workspacePath == "" || *terminalScript == "" {
		fmt.Fprintln(os.Stderr, "socket, workspace, and terminal-script are required")
		os.Exit(2)
	}

	workspace, err := filepath.EvalSymlinks(*workspacePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "resolve workspace: %v\n", err)
		os.Exit(1)
	}
	terminal, err := filepath.Abs(*terminalScript)
	if err != nil {
		fmt.Fprintf(os.Stderr, "resolve terminal script: %v\n", err)
		os.Exit(1)
	}
	if info, err := os.Stat(terminal); err != nil || !info.Mode().IsRegular() {
		fmt.Fprintln(os.Stderr, "VS Code terminal launcher not found")
		os.Exit(1)
	}

	if err := os.MkdirAll(filepath.Dir(*socketPath), 0700); err != nil {
		fmt.Fprintf(os.Stderr, "create socket directory: %v\n", err)
		os.Exit(1)
	}
	_ = os.Remove(*socketPath)
	listener, err := net.Listen("unix", *socketPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "listen on socket: %v\n", err)
		os.Exit(1)
	}
	defer func() {
		_ = listener.Close()
		_ = os.Remove(*socketPath)
	}()
	if err := os.Chmod(*socketPath, 0600); err != nil {
		fmt.Fprintf(os.Stderr, "set socket permissions: %v\n", err)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		_ = listener.Close()
	}()
	server := bridge{workspace: workspace, terminalScript: terminal}
	for {
		conn, err := listener.Accept()
		if err != nil {
			if ctx.Err() != nil {
				return
			}
			fmt.Fprintf(os.Stderr, "accept connection: %v\n", err)
			continue
		}
		go server.handle(conn)
	}
}
