//go:build !windows

package gala_tui

// EnableVTInput is a no-op on non-Windows platforms — Linux and macOS
// terminals interpret VT sequences from stdin natively. Always reports
// success.
//
// The Windows variant lives in `console_setup_windows.go` and calls
// SetConsoleMode to enable ENABLE_VIRTUAL_TERMINAL_INPUT.
func EnableVTInput() bool { return true }
