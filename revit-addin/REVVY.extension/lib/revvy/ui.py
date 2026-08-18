# -*- coding: utf-8 -*-
"""Dialog primitives built directly on Revit's native UI + .NET WinForms.

WORKAROUND, not a stylistic choice: on this pyRevit build (confirmed across
both the latest release and the first release with Revit 2027 support), the
Python-scripting-facing ``pyrevit.forms`` dialogs and ``script.get_output()``
console render as permanently blank -- confirmed even for pyRevit's own
built-in Reload command, so it is an upstream pyRevit/Revit-2027 rendering
bug, not something specific to this extension. Everything in this module
goes through ``Autodesk.Revit.UI.TaskDialog`` (native Win32, always part of
the Revit host) and a hand-built ``System.Windows.Forms`` input box instead,
neither of which passes through pyRevit's broken forms/output pipeline.

If a future pyRevit/Revit update fixes the upstream bug, this module can be
swapped back for ``pyrevit.forms`` without touching call sites much -- the
functions here intentionally mirror ``forms.ask_for_string`` /
``forms.alert`` / ``forms.CommandSwitchWindow`` shapes (return `None` on
cancel, etc.).
"""
import clr  # type: ignore

clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.Revit.UI import (  # type: ignore
    TaskDialog,
    TaskDialogCommandLinkId,
    TaskDialogCommonButtons,
    TaskDialogIcon,
    TaskDialogResult,
)
from System.Drawing import Point, Size  # type: ignore
from System.Windows.Forms import (  # type: ignore
    AnchorStyles,
    Button,
    DialogResult,
    Form,
    FormBorderStyle,
    FormStartPosition,
    Label,
    TextBox,
)

_COMMAND_LINK_IDS = [
    TaskDialogCommandLinkId.CommandLink1,
    TaskDialogCommandLinkId.CommandLink2,
    TaskDialogCommandLinkId.CommandLink3,
    TaskDialogCommandLinkId.CommandLink4,
]
_COMMAND_LINK_RESULTS = {
    TaskDialogResult.CommandLink1: 0,
    TaskDialogResult.CommandLink2: 1,
    TaskDialogResult.CommandLink3: 2,
    TaskDialogResult.CommandLink4: 3,
}


def ask_string(prompt, title="REVVY", is_password=False, default=""):
    """Modal single-line text entry. Returns None if the user cancels."""
    form = Form()
    form.Text = title
    form.ClientSize = Size(420, 120)
    form.FormBorderStyle = FormBorderStyle.FixedDialog
    form.StartPosition = FormStartPosition.CenterScreen
    form.MinimizeBox = False
    form.MaximizeBox = False
    form.TopMost = True

    label = Label()
    label.Text = prompt
    label.Location = Point(12, 12)
    label.Size = Size(396, 36)
    form.Controls.Add(label)

    textbox = TextBox()
    textbox.Location = Point(12, 50)
    textbox.Size = Size(396, 24)
    textbox.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
    textbox.Text = default
    if is_password:
        textbox.UseSystemPasswordChar = True
    form.Controls.Add(textbox)

    ok_button = Button()
    ok_button.Text = "OK"
    ok_button.Location = Point(252, 84)
    ok_button.Size = Size(75, 26)
    ok_button.DialogResult = DialogResult.OK
    form.Controls.Add(ok_button)
    form.AcceptButton = ok_button

    cancel_button = Button()
    cancel_button.Text = "Cancel"
    cancel_button.Location = Point(333, 84)
    cancel_button.Size = Size(75, 26)
    cancel_button.DialogResult = DialogResult.Cancel
    form.Controls.Add(cancel_button)
    form.CancelButton = cancel_button

    form.ActiveControl = textbox
    result = form.ShowDialog()
    if result == DialogResult.OK and textbox.Text:
        return textbox.Text
    return None


def alert(message, title="REVVY", warn=False):
    """Non-blocking-content informational dialog (single OK button)."""
    td = TaskDialog(title)
    td.MainInstruction = title
    td.MainContent = message
    if warn:
        td.MainIcon = TaskDialogIcon.TaskDialogIconWarning
    td.CommonButtons = TaskDialogCommonButtons.Ok
    td.Show()


def confirm(message, title="REVVY", warn=False):
    """Yes/No dialog. Returns True only if the user picks Yes."""
    td = TaskDialog(title)
    td.MainInstruction = title
    td.MainContent = message
    if warn:
        td.MainIcon = TaskDialogIcon.TaskDialogIconWarning
    td.CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No
    return td.Show() == TaskDialogResult.Yes


def choose(options, title="REVVY", message=""):
    """Up to 4 command-link choices. Returns the chosen option's text, or None."""
    if not options:
        return None
    if len(options) > 4:
        options = options[:4]

    td = TaskDialog(title)
    td.MainInstruction = message or title
    td.CommonButtons = TaskDialogCommonButtons.Cancel
    for link_id, option_text in zip(_COMMAND_LINK_IDS, options):
        td.AddCommandLink(link_id, option_text)

    result = td.Show()
    index = _COMMAND_LINK_RESULTS.get(result)
    if index is None or index >= len(options):
        return None
    return options[index]


def show_report(main_instruction, content, title="REVVY", expanded_content=None, warn=False):
    """Informational report with an optional collapsible details section."""
    td = TaskDialog(title)
    td.MainInstruction = main_instruction
    td.MainContent = content
    if expanded_content:
        td.ExpandedContent = expanded_content
    if warn:
        td.MainIcon = TaskDialogIcon.TaskDialogIconWarning
    td.CommonButtons = TaskDialogCommonButtons.Ok
    td.Show()
