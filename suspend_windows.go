//go:build windows

package gala_tui

// canSuspend is always false on Windows: the console has no job control, so
// there is no shell to hand the terminal to and nothing that could resume a
// stopped process. SuspendCmd does nothing there.
func canSuspend() bool { return false }

// stopUntilContinued is never reached on Windows (canSuspend is false); it
// exists so the shared session code compiles on every platform.
func stopUntilContinued() {}

// terminalForeground is always true on Windows: a console has no background
// jobs, so the process that holds it always may change its modes.
func terminalForeground(fd int) bool { return true }
