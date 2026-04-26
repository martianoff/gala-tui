//go:build windows

package gala_tui

import (
	"os"

	"golang.org/x/sys/windows"
)

// EnableVTInput tells the Windows console to interpret incoming bytes as
// virtual-terminal sequences — including SGR mouse packets — instead of
// the legacy console-input-record API. Without this, the ANSI escape we
// write to enable mouse mode (`\x1b[?1006h`) is silently ignored on
// Windows PowerShell / cmd.exe.
//
// Idempotent. Returns true on success, false on any failure (the runtime
// keeps going in degraded mode — mouse just won't work).
//
// Linked into the build only on Windows; the non-Windows variant in
// `console_setup_other.go` is a no-op that always reports success.
func EnableVTInput() bool {
	stdin := windows.Handle(os.Stdin.Fd())
	stdout := windows.Handle(os.Stdout.Fd())

	var inMode uint32
	if err := windows.GetConsoleMode(stdin, &inMode); err != nil {
		return false
	}
	// Console input modes — see
	// https://learn.microsoft.com/en-us/windows/console/setconsolemode
	//
	//   ENABLE_VIRTUAL_TERMINAL_INPUT routes input as ANSI escape
	//     sequences via ReadFile (instead of legacy InputRecords via
	//     ReadConsoleInput). Required for our VT mouse parser to work.
	//   ENABLE_MOUSE_INPUT lets mouse events through at all — without
	//     it the OS filters them at console-host level *before*
	//     anything reaches stdin, regardless of VT input mode. This
	//     was the missing piece causing clicks to be silently dropped.
	//   ENABLE_EXTENDED_FLAGS lets us toggle ENABLE_QUICK_EDIT_MODE.
	//   ENABLE_QUICK_EDIT_MODE (CLEARED): when on, the user's left-
	//     drag enters the conhost text-selection rectangle and our
	//     mouse events never fire. Must be off for click capture.
	const enableMouseInput = 0x0010
	const enableExtended   = 0x0080
	const enableQuickEdit  = 0x0040
	const enableVTInput    = 0x0200
	inMode = (inMode | enableMouseInput | enableExtended | enableVTInput) &^ enableQuickEdit
	if err := windows.SetConsoleMode(stdin, inMode); err != nil {
		return false
	}

	// Mirror on stdout — VT *output* processing is normally on under
	// modern terminals, but explicitly enabling guards against legacy
	// console hosts.
	var outMode uint32
	if err := windows.GetConsoleMode(stdout, &outMode); err != nil {
		return false
	}
	const enableVTOutput = 0x0004
	outMode |= enableVTOutput
	if err := windows.SetConsoleMode(stdout, outMode); err != nil {
		return false
	}
	return true
}
