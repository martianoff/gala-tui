//go:build !windows

package gala_tui

import (
	"fmt"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

// canSuspend reports whether stopping this process hands the terminal to a
// shell that can resume it.
//
// That is the question of whether our process group is orphaned. The kernel
// discards SIGTSTP sent to an orphaned group (POSIX: nobody is left to send
// SIGCONT), so stopping there would not stop at all — and stopUntilContinued
// would then wait for a SIGCONT that never comes, with the terminal already
// handed back in cooked mode. A group is not orphaned when one of its members
// has a parent in a different group of the same session: the job-control
// shell. Walk up through the processes that share our group (a `sudo` or a
// `go run` between us and the shell) to the first ancestor outside it, and
// ask whether it is in our session.
//
// Ancestors past the direct parent are found through /proc. Where there is
// no /proc (macOS) only the direct parent is checked, which covers a program
// started from a shell and answers "no" — the safe answer — otherwise.
func canSuspend() bool {
	// Ignored, SIGTSTP stops nothing, and stopUntilContinued would wait for
	// a SIGCONT that never comes.
	if signal.Ignored(syscall.SIGTSTP) {
		return false
	}
	pgrp := unix.Getpgrp()
	sid, err := unix.Getsid(0)
	if err != nil {
		return false
	}
	// PID 1 is walked too: in a container the interactive shell often is PID
	// 1, and it resumes jobs like any other shell. Past it there is nothing.
	pid := os.Getppid()
	for pid > 0 {
		pg, err := unix.Getpgid(pid)
		if err != nil {
			return false
		}
		if pg != pgrp {
			psid, err := unix.Getsid(pid)
			return err == nil && psid == sid
		}
		next, ok := procParent(pid)
		if !ok || next == pid {
			return false
		}
		pid = next
	}
	return false
}

// procParent reads a process's parent from /proc/<pid>/stat. The command
// name in field 2 is parenthesised and may itself contain spaces or
// parentheses, so the fields are counted from the last ')'.
func procParent(pid int) (int, bool) {
	b, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))
	if err != nil {
		return 0, false
	}
	s := string(b)
	i := strings.LastIndexByte(s, ')')
	if i < 0 {
		return 0, false
	}
	f := strings.Fields(s[i+1:])
	if len(f) < 2 {
		return 0, false
	}
	ppid, err := strconv.Atoi(f[1])
	return ppid, err == nil
}

// stopUntilContinued stops the process group, as Ctrl+Z would have in cooked
// mode, and returns once the shell has continued it in the foreground.
//
// The whole group, not just this process: a pipeline (`app | tee log`) is one
// job, and the shell expects all of it to stop. Waiting for SIGCONT rather
// than returning when kill does is what keeps the caller from retaking the
// terminal early — a self-sent stop is not guaranteed to have taken effect
// by the time kill returns.
//
// A SIGCONT is not always `fg`:
//
//   - `bg` continues the job in the background, where the terminal is the
//     shell's. Retaking it from there would stop the process again anyway
//     (SIGTTOU), so it stops itself again and waits for `fg`.
//   - `kill %1` sends SIGTERM along with the SIGCONT, and the cleanup guard
//     is exiting. Nothing to retake: this waits for the exit. The pause first
//     gives the guard, woken by the same delivery, time to say so.
func stopUntilContinued() {
	cont := make(chan os.Signal, 1)
	signal.Notify(cont, syscall.SIGCONT)
	defer signal.Stop(cont)
	for {
		if err := syscall.Kill(0, syscall.SIGTSTP); err != nil {
			return
		}
		<-cont
		time.Sleep(20 * time.Millisecond)
		if exiting.Load() {
			select {}
		}
		if terminalForeground(int(os.Stdin.Fd())) {
			return
		}
	}
}

// terminalForeground reports whether this process's group owns the terminal
// on fd — whether it may change the terminal's modes without being stopped
// for it. Not knowing counts as yes, which is how every run began.
func terminalForeground(fd int) bool {
	pg, err := unix.IoctlGetInt(fd, unix.TIOCGPGRP)
	return err != nil || pg == unix.Getpgrp()
}
