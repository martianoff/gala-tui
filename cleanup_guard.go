package gala_tui

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"golang.org/x/term"
)

// installCleanupGuard registers a SIGINT / SIGTERM handler that emits
// the terminal-state-restore escape codes before the process dies.
//
// Why we need this: gala-tui's normal cleanup path uses Go `defer` to
// run ansiAltScreenOff / ansiCursorShow / (optionally) ansiMouseOff and
// then term.Restore. defer fires on normal returns and on `panic`, but
// it does NOT fire on:
//
//   - signals (default Go behavior is to terminate without unwinding)
//   - os.Exit() calls anywhere in the program
//   - SIGKILL (no signal can be caught for this — out of scope)
//
// Without the guard, a Ctrl+C / kill / `bazel build` replacing the exe
// while it's still running leaves PowerShell stuck in mouse-tracking
// mode + cursor hidden + alt-screen on. The user sees raw mouse-event
// escape codes (`[NNN;col;rowM`) printed as text in their shell with
// no way to recover except closing the tab.
//
// We register one handler; SIGINT and SIGTERM both route through it.
// useMouse is true only for RunWithMouse — the other entry points
// don't enable mouse mode so we skip the disable code (writing it
// when the mode wasn't enabled is a no-op but spammy).
//
// The handler runs in its own goroutine. After cleanup it exits with
// 128+SIGINT (the conventional code for SIGINT-terminated programs)
// rather than re-raising the signal, because Go's signal.Notify
// already swallowed the default-action so re-raising would just
// loop right back into our handler.
func installCleanupGuard(fd int, state *term.State, useMouse bool) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigCh
		if useMouse {
			fmt.Fprint(os.Stdout, ansiMouseOff())
		}
		fmt.Fprint(os.Stdout, ansiCursorShow())
		fmt.Fprint(os.Stdout, ansiAltScreenOff())
		_ = term.Restore(fd, state)
		os.Exit(130)
	}()
}
