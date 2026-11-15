package main

import (
	"bufio"
	"context"
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
	containerName   string
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

func remoteFolderURI(containerID, folderPath string) string {
	authority := hex.EncodeToString([]byte(containerID))
	return fmt.Sprintf("vscode-remote://attached-container+%s%s", authority, folderPath)
}

func resolveContainerID(containerName string) (string, error) {
	output, err := exec.Command("docker", "inspect", "--format", "{{.Id}}", containerName).Output()
	if err != nil {
		return "", fmt.Errorf("Unable to inspect DevBox container %q: %w", containerName, err)
	}
	containerID := strings.TrimSpace(string(output))
	if len(containerID) != 64 {
		return "", fmt.Errorf("Docker returned an invalid container ID for %q", containerName)
	}
	return containerID, nil
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
	containerID, err := resolveContainerID(b.containerName)
	if err != nil {
		return err
	}
	vscode, err := exec.LookPath("code")
	if err != nil {
		return errors.New("VS Code CLI 'code' was not found on the host PATH. Install VS Code and make its 'code' command available.")
	}
	extensions, err := exec.Command(vscode, "--list-extensions").Output()
	if err != nil {
		return fmt.Errorf("Unable to inspect VS Code extensions: %v", err)
	}
	if !strings.Contains(strings.ToLower(string(extensions)), "ms-vscode-remote.remote-containers") {
		return errors.New("The VS Code 'Dev Containers' extension is required. Install ms-vscode-remote.remote-containers on the host and try again.")
	}
	remoteURI := remoteFolderURI(containerID, containerFolder)
	cmd := exec.Command(vscode, "--new-window", "--folder-uri", remoteURI)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = nil, nil, nil
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("Unable to start VS Code remote session: %v", err)
	}
	_ = cmd.Process.Release()
	return nil
}

func main() {
	socketPath := flag.String("socket", "", "Unix socket path")
	workspacePath := flag.String("workspace", "", "Host workspace path")
	containerName := flag.String("container", "devbox", "Running Docker container name")
	flag.Parse()
	if *socketPath == "" || *workspacePath == "" || *containerName == "" {
		fmt.Fprintln(os.Stderr, "socket, workspace, and container are required")
		os.Exit(2)
	}

	workspace, err := filepath.EvalSymlinks(*workspacePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "resolve workspace: %v\n", err)
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
	server := bridge{workspace: workspace, containerName: *containerName}
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
