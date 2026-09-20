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
//
// modesOff is the input-mode disable string for this run, built by
// termModesOff in runtime.gala — mouse tracking, bracketed paste, focus
// reporting and the kitty keyboard flag, in whatever combination
// enterTermSession turned on. It is passed in rather than recomputed
// here so this path and TermSession.Close emit byte-for-byte the same
// restore sequence: a mode added to one and forgotten in the other
// means Ctrl+C leaves the user's terminal in a state the ordinary exit
// would have cleaned up (paste markers in their next command line, raw
// mouse packets printed on every click, Esc arriving as `CSI 27 u`).
// Entry points that enable nothing pass an empty string.
//
// The handler runs in its own goroutine. After cleanup it exits with
// 128+SIGINT (the conventional code for SIGINT-terminated programs)
// rather than re-raising the signal, because Go's signal.Notify
// already swallowed the default-action so re-raising would just
// loop right back into our handler.
func installCleanupGuard(fd int, state *term.State, modesOff string) {
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigCh
		fmt.Fprint(os.Stdout, modesOff)
		fmt.Fprint(os.Stdout, ansiCursorShow())
		fmt.Fprint(os.Stdout, ansiAltScreenOff())
		_ = term.Restore(fd, state)
		os.Exit(130)
	}()
}
