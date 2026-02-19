import time
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk
from pylsl import resolve_streams, StreamInlet

from collections import deque

from tkinter import messagebox



SCAN_SETTLE_SEC = 2

MOVE_PIXELS = 10
TICK_MS = 1000  # how often we compare values & move
FAILSAFE_MS = 30_000   # 30 seconds


# class PlayerPanel:
#     def __init__(self, parent, title: str, desired_source_id: str):
#         self.desired_source_id = desired_source_id

#         self.frame = ttk.LabelFrame(parent, text=title, padding=6)


#         self.found_var = tk.StringVar(value="Not scanned yet")
#         ttk.Label(self.frame, textvariable=self.found_var).pack(anchor="w", pady=(0, 10))

#         self.name_var = tk.StringVar(value="")
#         self.type_var = tk.StringVar(value="")
#         self.sourceid_var = tk.StringVar(value="")
#         self.value_var = tk.StringVar(value="")

#         self._row("name", self.name_var)
#         self._row("type", self.type_var)
#         self._row("source_id", self.sourceid_var)
#         self._row("value", self.value_var)

#         self.inlet = None
#         self.stop_event = threading.Event()
#         self.reader_thread = None

#         self.latest_value = None  # <- numeric value used by the game logic

#     def _row(self, label, var):
#         row = ttk.Frame(self.frame)
#         row.pack(fill=tk.X, pady=2)
#         ttk.Label(row, text=f"{label}:", width=8).pack(side=tk.LEFT)
#         ttk.Label(row, textvariable=var).pack(side=tk.LEFT)

#     def clear(self):
#         self.found_var.set("Not found")
#         self.name_var.set("")
#         self.type_var.set("")
#         self.sourceid_var.set("")
#         self.value_var.set("")
#         self.latest_value = None
#         self.stop()

#     def bind_stream(self, stream_info):
#         self.found_var.set("Found player stream ✅")
#         self.name_var.set(stream_info.name())
#         self.type_var.set(stream_info.type())
#         self.sourceid_var.set(stream_info.source_id())
#         self.start_reader(stream_info)

#     def start_reader(self, stream_info):
#         self.stop()
#         self.stop_event = threading.Event()
#         self.value_var.set("")
#         self.latest_value = None

#         self.inlet = StreamInlet(stream_info)
#         self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
#         self.reader_thread.start()

#     def reader_loop(self):
#         while not self.stop_event.is_set():
#             sample, ts = self.inlet.pull_sample(timeout=0.5)
#             if sample is None:
#                 continue
#             if not sample:
#                 continue

#             v = sample[0]
#             self.latest_value = v

#             # update UI safely
#             self.frame.after(0, lambda val=v: self.value_var.set(f"{val:.6f}"))

#     def stop(self):
#         self.stop_event.set()
class PlayerPanel:
    def __init__(self, parent, title: str, name_var: str, desired_source_id: str):
        self.desired_source_id = desired_source_id

        self.frame = ttk.LabelFrame(parent, text=title, padding=6)

        self.found_var = tk.StringVar(value="Not scanned yet")
        ttk.Label(self.frame, textvariable=self.found_var).pack(anchor="w", pady=(0, 10))

        self.name_var = tk.StringVar(value="")
        self.type_var = tk.StringVar(value="")
        self.sourceid_var = tk.StringVar(value="")
        self.value_var = tk.StringVar(value="")

        self._row("name", self.name_var)
        self._row("type", self.type_var)
        self._row("source_id", self.sourceid_var)
        self._row("value", self.value_var)

        self.inlet = None
        self.stop_event = threading.Event()
        self.reader_thread = None

        # Latest (for display/debug)
        self.latest_value = None

        # Queue of *new* values so the game can consume them exactly once
        self._q = deque()
        self._q_lock = threading.Lock()

    def _row(self, label, var):
        row = ttk.Frame(self.frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=f"{label}:", width=8).pack(side=tk.LEFT)
        ttk.Label(row, textvariable=var).pack(side=tk.LEFT)

    def clear(self):
        self.found_var.set("Not found")
        self.name_var.set("")
        self.type_var.set("")
        self.sourceid_var.set("")
        self.value_var.set("")
        self.latest_value = None
        with self._q_lock:
            self._q.clear()
        self.stop()

    def bind_stream(self, stream_info):
        self.found_var.set("Found player stream ✅")
        self.name_var.set(stream_info.name())
        self.type_var.set(stream_info.type())
        self.sourceid_var.set(stream_info.source_id())
        self.start_reader(stream_info)

    def start_reader(self, stream_info):
        self.stop()
        self.stop_event = threading.Event()
        self.value_var.set("")
        self.latest_value = None
        with self._q_lock:
            self._q.clear()

        self.inlet = StreamInlet(stream_info)
        self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
        self.reader_thread.start()

    def reader_loop(self):
        while not self.stop_event.is_set():
            sample, ts = self.inlet.pull_sample(timeout=0.5)
            if not sample:
                continue

            v = sample[0]
            self.latest_value = v

            # Push into queue so game loop can consume each value once
            with self._q_lock:
                self._q.append(v)

            # update UI safely
            self.frame.after(0, lambda val=v: self.value_var.set(f"{val:.6f}"))

    def get_next_value(self):
        """Return the most recently received value (and drop older queued values)."""
        with self._q_lock:
            if not self._q:
                return None
            latest = self._q[-1]   # most recent
            self._q.clear()        # drop backlog so we don't lag
            return latest

    def stop(self):
        self.stop_event.set()



class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Two-Player EEG Bind (LSL)")
        self._failsafe_after_id = None


        # Fullscreen-ish by default (macOS/Windows usually)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            # fallback
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()
            self.root.geometry(f"{w}x{h}+0+0")

        outer = ttk.Frame(self.root, padding=2)
        outer.pack(fill=tk.BOTH, expand=True)

        # Left panel (Player 1)
        # self.left = PlayerPanel(outer, "Player 1", desired_source_id="player1_mock")
        # self.left.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        PANEL_W = 260   # try 220–320
        PANEL_PAD = 6

        # Left panel
        self.left = PlayerPanel(outer, "Player 1", name_var = "Muse-FDCA_band", desired_source_id="")
        self.left.frame.config(width=PANEL_W, padding=6)
        self.left.frame.pack_propagate(False)  # IMPORTANT: keep the width you set
        self.left.frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, PANEL_PAD))


        # Center column: canvas + buttons
        center = ttk.Frame(outer, padding=10)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, PANEL_PAD))

        # --- Canvas area for goalposts + moving logo ---
        # self.canvas = tk.Canvas(center, width=600, height=350, highlightthickness=0)
        # self.canvas.pack(pady=(10, 10))
        self.canvas = tk.Canvas(center, height=350, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=(10, 10))


        # Load images (change these paths if needed)
        self.goal_path = "/Users/sidabid09/Downloads/goalpost.png"
        self.logo_path = "/Users/sidabid09/Downloads/NeuroTech Logo.jpg"

        self.goal_img = None
        self.logo_img = None
        self.goal_left_id = None
        self.goal_right_id = None
        self.logo_id = None

        self._load_and_place_images()

        # Buttons
        self.scan_btn = ttk.Button(center, text="Scan & Bind Players", command=self.scan_and_bind)
        self.scan_btn.pack(pady=(10, 6))

       # self.start_btn = ttk.Button(center, text="Start", command=self.start_game, state="disabled")
        self.start_btn = ttk.Button(center, text="Start", command=self.toggle_game, state="disabled")

        self.start_btn.pack(pady=(0, 10))

        self.reset_btn = ttk.Button(center, text="Reset", command=self.reset_game, state="disabled")
        self.reset_btn.pack(pady=(0, 10))


        self.status_var = tk.StringVar(value="Click 'Scan & Bind Players'.")
        ttk.Label(center, textvariable=self.status_var, wraplength=260, justify="center").pack()

        # Right panel (Player 2)
        # self.right = PlayerPanel(outer, "Player 2", desired_source_id="player2_mock")
        # self.right.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        self.right = PlayerPanel(outer, "Player 2", name_var = "Muse-07D2_band", desired_source_id="")
        self.right.frame.config(width=PANEL_W, padding=6)
        self.right.frame.pack_propagate(False)
        self.right.frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 0))

        self.scanning = False
        self.game_running = False

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # If window resizes, re-center art
        # self.root.bind("<Configure>", lambda e: self._recenter_canvas_art())
        self._last_canvas_size = (None, None)
        self._logo_initialized = False

        self.canvas.bind("<Configure>", lambda e: self._recenter_canvas_art())
    # def toggle_game(self):
    #     if self.game_running:
    #         # STOP / PAUSE
    #         self.game_running = False
    #         self.start_btn.config(text="Start")
    #         self.status_var.set("Paused.")
    #         return

    #     # START / RESUME
    #     self.game_running = True
    #     self.start_btn.config(text="Stop")
    #     self.status_var.set("Game running: consuming new samples and moving logo once per pair...")
    #     self._game_tick()
        
    def toggle_game(self):
        if self.game_running:
            # STOP / PAUSE
            self.game_running = False
            self.start_btn.config(text="Start")
            self.status_var.set("Paused.")

            # cancel failsafe if running
            if self._failsafe_after_id:
                self.root.after_cancel(self._failsafe_after_id)
                self._failsafe_after_id = None
            return

        # START / RESUME
        self.game_running = True
        self.start_btn.config(text="Stop")
        self.reset_btn.config(state="disabled")
        self.status_var.set("Game running: consuming new samples and moving logo once per pair...")

        # start failsafe timer
        self._failsafe_after_id = self.root.after(FAILSAFE_MS, self._failsafe_trigger)

        self._game_tick()


    def _stop_game_ui(self, status="Paused."):
        self.game_running = False
        self.start_btn.config(text="Start")
        self.status_var.set(status)

    # def _handle_win(self, winner: str):
    #     # stop/pause the game
    #     self._stop_game_ui(status=f"{winner} wins!")
    #     self.reset_btn.config(state="normal")

    #     # popup
    #     messagebox.showinfo("Winner!", f"{winner} Wins!")
    def _handle_win(self, winner: str):
    # cancel failsafe
        if self._failsafe_after_id:
            self.root.after_cancel(self._failsafe_after_id)
            self._failsafe_after_id = None

        self._stop_game_ui(status=f"{winner} wins!")
        self.reset_btn.config(state="normal")

        messagebox.showinfo("Winner!", f"{winner} Wins!")


    def _check_winner(self) -> bool:
        """Return True if someone won (and we handled it)."""
        logo_bb = self.canvas.bbox(self.logo_id)
        left_bb = self.canvas.bbox(self.goal_left_id)
        right_bb = self.canvas.bbox(self.goal_right_id)

        if not logo_bb or not left_bb or not right_bb:
            return False

        def intersects(a, b):
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)

        # Touch left goalpost => Player 2 wins
        if intersects(logo_bb, left_bb):
            self._handle_win("Player 2")
            return True

        # Touch right goalpost => Player 1 wins
        if intersects(logo_bb, right_bb):
            self._handle_win("Player 1")
            return True

        return False
    
    def _failsafe_trigger(self):
        if not self.game_running:
            return

        # Determine nearest goal
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        logo_x, logo_y = self.canvas.coords(self.logo_id)

        # Distance to each goal center
        left_goal_x, _ = self.canvas.coords(self.goal_left_id)
        right_goal_x, _ = self.canvas.coords(self.goal_right_id)

        dist_left = abs(logo_x - left_goal_x)
        dist_right = abs(logo_x - right_goal_x)

        if dist_left <= dist_right:
            # Snap to left goal → Player 2 wins
            self.canvas.coords(self.logo_id, left_goal_x, logo_y)
            self._handle_win("Player 2")
        else:
            # Snap to right goal → Player 1 wins
            self.canvas.coords(self.logo_id, right_goal_x, logo_y)
            self._handle_win("Player 1")


    def reset_game(self):
        """
        Reset to square one:
        - stop game loop
        - stop reader threads
        - clear panels
        - require scan & bind again
        - re-center logo
        """
        self.game_running = False

        # stop streams/threads
        self.left.stop()
        self.right.stop()

        # clear UI panels
        self.left.clear()
        self.right.clear()
        self.left.found_var.set("Not scanned yet")
        self.right.found_var.set("Not scanned yet")

        # buttons back to initial state
        self.start_btn.config(text="Start", state="disabled")
        self.reset_btn.config(state="disabled")
        self.scan_btn.config(state="normal")

        self.status_var.set("Reset. Click 'Scan & Bind Players' to begin again.")

        # clear any queued values just in case
        # (clear() already does this, but harmless)
        # re-center logo
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw > 1 and ch > 1:
            y_mid = ch // 2
            self.canvas.coords(self.logo_id, cw // 2, y_mid)



    def _load_and_place_images(self):
        # Goalposts
        goal = Image.open(self.goal_path)
        # Scale goalposts to fit nicely
        goal = goal.resize((180, 120))
        self.goal_img = ImageTk.PhotoImage(goal)

        # Logo
        logo = Image.open(self.logo_path)
        logo = logo.resize((110, 110))
        self.logo_img = ImageTk.PhotoImage(logo)

        # Create items (initial placement; we’ll recenter after)
        self.goal_left_id = self.canvas.create_image(0, 0, image=self.goal_img, anchor="w")
        self.goal_right_id = self.canvas.create_image(0, 0, image=self.goal_img, anchor="e")
        self.logo_id = self.canvas.create_image(0, 0, image=self.logo_img, anchor="center")

        self._recenter_canvas_art()

    # def _recenter_canvas_art(self):
    #     # Place items based on current canvas size
    #     cw = self.canvas.winfo_width()
    #     ch = self.canvas.winfo_height()
    #     if cw <= 1 or ch <= 1:
    #         return

    #     y_mid = ch // 2
    #     padding = 2 #or 0

    #     # Left goalpost at far left
    #     self.canvas.coords(self.goal_left_id, padding, y_mid)
    #     # Right goalpost at far right
    #     self.canvas.coords(self.goal_right_id, cw - padding, y_mid)
    #     # Logo at center
    #     self.canvas.coords(self.logo_id, cw // 2, y_mid)
    def _recenter_canvas_art(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        # Only act if canvas size actually changed
        if (cw, ch) == self._last_canvas_size:
            return
        self._last_canvas_size = (cw, ch)

        y_mid = ch // 2
        padding = 2

        # Goalposts stick to edges
        self.canvas.coords(self.goal_left_id, padding, y_mid)
        self.canvas.coords(self.goal_right_id, cw - padding, y_mid)

        # Logo: center ONLY the first time; afterwards keep x, just update y and clamp
        if not self._logo_initialized:
            self.canvas.coords(self.logo_id, cw // 2, y_mid)
            self._logo_initialized = True
        else:
            x, _ = self.canvas.coords(self.logo_id)
            # Clamp to new bounds after resize
            pad = 60
            x = max(pad, min(cw - pad, x))
            self.canvas.coords(self.logo_id, x, y_mid)


    def scan_and_bind(self):
        if self.scanning:
            return
        self.scanning = True
        self.scan_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.status_var.set("Scanning for EEG streams... (waiting 2 seconds first)")

        def worker():
            try:
                time.sleep(SCAN_SETTLE_SEC)
                streams = resolve_streams()

                p1 = None
                p2 = None
                for s in streams:
                    if s.name() == "Muse-FDCA_band":
                        p1 = s
                    elif s.name() == "Muse-07D2_band":
                        p2 = s

                def apply():
                    self.left.clear()
                    self.right.clear()

                    if p1:
                        self.left.bind_stream(p1)
                    else:
                        self.left.found_var.set("Not found ❌ (player1_mock)")

                    if p2:
                        self.right.bind_stream(p2)
                    else:
                        self.right.found_var.set("Not found ❌ (player2_mock)")

                    self.status_var.set(
                        f"Found {len(streams)} total stream(s). "
                        f"P1={'yes' if p1 else 'no'}, P2={'yes' if p2 else 'no'}."
                    )

                    # Enable Start only if both are bound
                    if p1 and p2:
                        self.start_btn.config(state="normal")

                self.root.after(0, apply)

            finally:
                def done():
                    self.scanning = False
                    self.scan_btn.config(state="normal")
                self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def start_game(self):
        if self.game_running:
            return
        self.game_running = True
        self.start_btn.config(state="disabled")
        self.status_var.set("Game running: comparing values and moving logo...")

        self._game_tick()
    
    def _game_tick(self):
        if not self.game_running:
            return

        # Pull exactly one new value from each queue (if available)
        v1 = self.left.get_next_value()
        v2 = self.right.get_next_value()

        # Only move if BOTH produced a new value
        if v1 is not None and v2 is not None:
            if v1 < v2:
                self._move_logo(dx=-MOVE_PIXELS)
            elif v2 < v1:
                self._move_logo(dx=+MOVE_PIXELS)
            # equal => no move

        # Poll fairly often; movement will still be once per new pair
        self.root.after(TICK_MS, self._game_tick)


    # def _game_tick(self):
    #     if not self.game_running:
    #         return

    #     v1 = self.left.latest_value
    #     v2 = self.right.latest_value

    #     # Only move if we have both values
    #     if v1 is not None and v2 is not None:
    #         # NOTE: I assume you meant P2 < P1 => move RIGHT (not left).
    #         if v1 < v2:
    #             self._move_logo(dx=-MOVE_PIXELS)
    #         elif v2 < v1:
    #             self._move_logo(dx=+MOVE_PIXELS)
    #         # equal => no move

    #     self.root.after(TICK_MS, self._game_tick)

    def _move_logo(self, dx: int):
        # Keep logo inside the “field” between goalposts
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        x, y = self.canvas.coords(self.logo_id)

        # Rough boundaries: keep it inside canvas with some padding
        pad = 60
        new_x = max(pad, min(cw - pad, x + dx))

        self.canvas.coords(self.logo_id, new_x, y)
        self._check_winner()

    def on_close(self):
        self.game_running = False
        self.left.stop()
        self.right.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
