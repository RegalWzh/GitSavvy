import os

import sublime
from sublime_plugin import EventListener, WindowCommand

from . import util
from ..core.settings import SettingsMixin


IGNORE_NEXT_ACTIVATE = False


class GsInterfaceFocusEventListener(EventListener):

    """
    Trigger handlers for view life-cycle events.
    """

    def on_activated(self, view):
        global IGNORE_NEXT_ACTIVATE

        # When the user just opened e.g. the goto or command palette overlay
        # prevent a refresh signal on closing that panel.
        # Whitelist "Terminus" which reports itself as a widget as well.
        if view.settings().get('is_widget') and not view.settings().get("terminus_view"):
            IGNORE_NEXT_ACTIVATE = True
        elif IGNORE_NEXT_ACTIVATE:
            IGNORE_NEXT_ACTIVATE = False
        else:
            # status bar is handled by GsStatusBarEventListener
            util.view.refresh_gitsavvy(view, refresh_status_bar=False)

    def on_close(self, view):
        util.view.handle_closed_view(view)


NATIVE_GIT_EDITOR_FILES = {
    'MERGE_MSG',
    'COMMIT_EDITMSG',
    'PULLREQ_EDITMSG',
    'git-rebase-todo',
}


class GitCommandFromTerminal(EventListener, SettingsMixin):
    def on_load(self, view):
        # type: (sublime.View) -> None
        file_path = view.file_name()
        if file_path and os.path.basename(file_path) in NATIVE_GIT_EDITOR_FILES:
            view.set_scratch(True)

    def on_pre_close(self, view):
        # type: (sublime.View) -> None
        file_path = view.file_name()
        if file_path and os.path.basename(file_path) in NATIVE_GIT_EDITOR_FILES:
            view.run_command("save")


PROJECT_MSG = """
<body>
<p>Add the key <code>"GitSavvy"</code> as follows</p>
<code>
{<br>
  "settings": {<br>
    "GitSavvy": {<br>
        // GitSavvy settings go here<br>
    }<br>
  }<br>
}<br>
</code>
</body>
""".replace(" ", "&nbsp;")


class KeyboardSettingsListener(EventListener):
    def on_post_window_command(self, window, command, args):
        if command == "edit_settings":
            base = args.get("base_file", "")
            if base.endswith("sublime-keymap") and "/GitSavvy/Default" in base:
                w = sublime.active_window()
                w.focus_group(0)
                w.run_command("open_file", {"file": "${packages}/GitSavvy/Default.sublime-keymap"})
                w.focus_group(1)
            elif args.get("user_file", "").endswith(".sublime-project"):
                w = sublime.active_window()
                view = w.active_view()
                data = window.project_data()
                if view and "GitSavvy" not in data.get("settings", {}):
                    sublime.set_timeout_async(
                        lambda: view.show_popup(PROJECT_MSG, max_width=550)  # type: ignore
                    )


class GsEditSettingsCommand(WindowCommand):
    """
    For some reasons, the command palette doesn't trigger `on_post_window_command` for
    dev version of Sublime Text. The command palette would call `gs_edit_settings` and
    subsequently trigger `on_post_window_command`.
    """
    def run(self, **kwargs):
        self.window.run_command("edit_settings", kwargs)


class GsEditProjectSettingsCommand(WindowCommand):
    """
    For some reasons, the command palette doesn't trigger `on_post_window_command` for
    dev version of Sublime Text. The command palette would call `gs_edit_settings` and
    subsequently trigger `on_post_window_command`.
    """
    def run(self):
        project_file_name = self.window.project_file_name()
        project_data = self.window.project_data()
        if not project_file_name or project_data is None:
            sublime.error_message("No project data found.")
            return

        sublime.set_timeout(lambda: self.window.run_command("edit_settings", {
            "user_file": project_file_name,
            "base_file": "${packages}/GitSavvy/GitSavvy.sublime-settings"
        }), 100)
