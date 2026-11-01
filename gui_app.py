"""
AI Traffic Speed Radar - Professional Windows Desktop Surveillance Station
Built with CustomTkinter, OpenCV, YOLOv8, and Windows Fluent Design.
"""
import os
import sys
import threading
import queue
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

from speed_radar.config import RadarConfig, VEHICLE_CLASSES
from speed_radar.radar_engine import TrafficSpeedRadar


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class WindowsSpeedRadarApp(ctk.CTk):
    """
    Professional Windows Desktop Surveillance Station for AI Traffic Speed Radar.
    """
    def __init__(self):
        super().__init__()

        # Window Metadata & Geometry
        self.title("AI Traffic Speed Radar - Surveillance Workstation")
        self.geometry("1440x900")
        self.minsize(1180, 720)

        # Core State
        self.radar_config = RadarConfig()
        self.radar_engine: Optional[TrafficSpeedRadar] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.is_processing = False
        self.is_paused = False
        self.frame_queue = queue.Queue(maxsize=3)
        self.selected_source = "traffic.mp4"
        self.active_frame_raw: Optional[np.ndarray] = None
        self.selected_snapshot_path: Optional[str] = None
        self.is_fullscreen = False

        # Build UI Architecture
        self._setup_windows_menu()
        self._build_layout()
        self._style_treeview()

        # Keyboard Shortcuts
        self._bind_shortcuts()

        # Start background polling
        self.after(30, self._update_gui_loop)
        # Auto-start monitoring on launch
        self.after(600, self._start_monitoring)

    # =========================================================================
    # WINDOWS NATIVE MENU BAR
    # =========================================================================
    def _setup_windows_menu(self):
        self.menu_bar = tk.Menu(self)

        # File Menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Open Video File...", accelerator="Ctrl+O", command=self._browse_file)
        file_menu.add_command(label="Connect Live Webcam (Cam 0)", accelerator="Ctrl+W", command=lambda: self._set_source("0"))
        file_menu.add_command(label="Load Bundled Highway Sample", command=lambda: self._set_source("traffic.mp4"))
        file_menu.add_separator()
        file_menu.add_command(label="Save Current Frame Snapshot...", accelerator="Ctrl+S", command=self._save_frame_snapshot)
        file_menu.add_command(label="Open Violations Directory", accelerator="Ctrl+D", command=self._open_snapshots_dir)
        file_menu.add_command(label="Open CSV Audit Log", command=self._open_csv_log)
        file_menu.add_separator()
        file_menu.add_command(label="Exit Surveillance", accelerator="Alt+F4", command=self._on_exit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Surveillance Menu
        surv_menu = tk.Menu(self.menu_bar, tearoff=0)
        surv_menu.add_command(label="Start Radar", accelerator="F5", command=self._start_monitoring)
        surv_menu.add_command(label="Pause / Resume", accelerator="Space", command=self._toggle_pause)
        surv_menu.add_command(label="Stop Radar", accelerator="Shift+F5", command=self._stop_monitoring)
        surv_menu.add_separator()
        surv_menu.add_command(label="Reset Session Counters", command=self._reset_counters)
        self.menu_bar.add_cascade(label="Surveillance", menu=surv_menu)

        # View Menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_show_hud = tk.BooleanVar(value=True)
        self.menu_show_badges = tk.BooleanVar(value=True)
        self.menu_show_trails = tk.BooleanVar(value=True)
        self.menu_show_gates = tk.BooleanVar(value=True)

        view_menu.add_checkbutton(label="Show Futuristic HUD Bar", variable=self.menu_show_hud, command=self._on_view_toggle)
        view_menu.add_checkbutton(label="Show Vehicle Speed Badges", variable=self.menu_show_badges, command=self._on_view_toggle)
        view_menu.add_checkbutton(label="Show Trajectory Motion Trails", variable=self.menu_show_trails, command=self._on_view_toggle)
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Fullscreen", accelerator="F11", command=self._toggle_fullscreen)
        self.menu_bar.add_cascade(label="View", menu=view_menu)

        # Tools Menu
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        tools_menu.add_command(label="Visual Gate Calibration Tool...", command=self._launch_calibrator)
        tools_menu.add_command(label="Explore Output Workspace", command=self._open_output_dir)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)

        # Help Menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="System & CUDA Diagnostics", command=self._show_diagnostics)
        help_menu.add_command(label="About AI Speed Radar", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=self.menu_bar)

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self._browse_file())
        self.bind("<Control-w>", lambda e: self._set_source("0"))
        self.bind("<Control-s>", lambda e: self._save_frame_snapshot())
        self.bind("<Control-d>", lambda e: self._open_snapshots_dir())
        self.bind("<F5>", lambda e: self._start_monitoring())
        self.bind("<Shift-F5>", lambda e: self._stop_monitoring())
        self.bind("<space>", lambda e: self._toggle_pause())
        self.bind("<F11>", lambda e: self._toggle_fullscreen())

    # =========================================================================
    # MAIN WINDOWS LAYOUT
    # =========================================================================
    def _build_layout(self):
        # Master grid: Top Toolbar (Row 0), Tabbed Content (Row 1), Status Bar (Row 2)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # -------------------------------------------------------------
        # 1. WINDOWS TOP TOOLBAR / ACTION STRIP
        # -------------------------------------------------------------
        toolbar = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color="#18181b", border_width=1, border_color="#27272a")
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(10, weight=1)

        # Title Brand
        title_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        title_box.pack(side="left", padx=14, pady=6)
        ctk.CTkLabel(title_box, text="⚡ AI SPEED RADAR", font=ctk.CTkFont(size=17, weight="bold"), text_color="#00E5FF").pack(side="left")
        ctk.CTkLabel(title_box, text=" WORKSTATION", font=ctk.CTkFont(size=14, weight="normal"), text_color="#A1A1AA").pack(side="left")

        # Action Buttons
        self.btn_start = ctk.CTkButton(
            toolbar, text="▶ Start Radar", width=115, height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00C853", hover_color="#009624",
            command=self._toggle_monitoring
        )
        self.btn_start.pack(side="left", padx=6, pady=6)

        self.btn_pause = ctk.CTkButton(
            toolbar, text="⏸ Pause", width=90, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#3F3F46", hover_color="#52525B",
            command=self._toggle_pause, state="disabled"
        )
        self.btn_pause.pack(side="left", padx=4, pady=6)

        self.btn_snapshot = ctk.CTkButton(
            toolbar, text="📸 Snapshot", width=100, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#27272A", hover_color="#3F3F46",
            command=self._save_frame_snapshot
        )
        self.btn_snapshot.pack(side="left", padx=4, pady=6)

        self.btn_calib = ctk.CTkButton(
            toolbar, text="🎯 Calibrate", width=95, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#27272A", hover_color="#3F3F46",
            command=self._launch_calibrator
        )
        self.btn_calib.pack(side="left", padx=4, pady=6)

        # Active Source indicator & browse button
        source_box = ctk.CTkFrame(toolbar, fg_color="#27272A", corner_radius=6)
        source_box.pack(side="left", padx=16, pady=8)

        ctk.CTkLabel(source_box, text="Source:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#A1A1AA").pack(side="left", padx=(8, 4))
        self.source_label = ctk.CTkLabel(source_box, text="traffic.mp4", font=ctk.CTkFont(family="Consolas", size=12), text_color="#FFFFFF")
        self.source_label.pack(side="left", padx=4)

        browse_btn = ctk.CTkButton(source_box, text="Browse...", width=65, height=26, font=ctk.CTkFont(size=11), fg_color="#3F3F46", hover_color="#52525B", command=self._browse_file)
        browse_btn.pack(side="left", padx=4, pady=2)

        # Status Pill Indicator
        self.status_pill = ctk.CTkLabel(
            toolbar,
            text="● RADAR ACTIVE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00E676"
        )
        self.status_pill.pack(side="right", padx=18)

        # -------------------------------------------------------------
        # 2. TABBED MAIN INTERFACE
        # -------------------------------------------------------------
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=10,
            fg_color="#121215",
            segmented_button_fg_color="#1E1E24",
            segmented_button_selected_color="#0078D4",
            segmented_button_selected_hover_color="#0063B1"
        )
        self.tabview.grid(row=1, column=0, padx=12, pady=(6, 4), sticky="nsew")

        self.tab_monitor = self.tabview.add("  🎥 Live Radar Monitor  ")
        self.tab_violations = self.tabview.add("  🚨 Violations & Evidence Gallery  ")
        self.tab_settings = self.tabview.add("  ⚙ Calibration & Settings  ")

        self._build_tab_monitor()
        self._build_tab_violations()
        self._build_tab_settings()

        # -------------------------------------------------------------
        # 3. WINDOWS MULTI-PANE STATUS BAR
        # -------------------------------------------------------------
        statusbar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#18181B", border_width=1, border_color="#27272A")
        statusbar.grid(row=2, column=0, sticky="ew")
        statusbar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.sb_status = ctk.CTkLabel(statusbar, text="Status: Radar Initialized", font=ctk.CTkFont(size=12), text_color="#D4D4D8", anchor="w")
        self.sb_status.grid(row=0, column=0, padx=12, sticky="w")

        device_name = "NVIDIA CUDA GPU (Enabled)" if (cv2.cuda.getCudaEnabledDeviceCount() > 0 or "torch" in sys.modules) else "CPU (Standard)"
        self.sb_engine = ctk.CTkLabel(statusbar, text=f"Inference: YOLOv8n | {device_name}", font=ctk.CTkFont(size=12), text_color="#A1A1AA", anchor="w")
        self.sb_engine.grid(row=0, column=1, padx=12, sticky="w")

        self.sb_res = ctk.CTkLabel(statusbar, text="Resolution: 1280x720 @ 30.0 FPS", font=ctk.CTkFont(size=12), text_color="#A1A1AA", anchor="w")
        self.sb_res.grid(row=0, column=2, padx=12, sticky="w")

        self.sb_metrics = ctk.CTkLabel(statusbar, text="Violations: 0 | Measured: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00E5FF", anchor="e")
        self.sb_metrics.grid(row=0, column=3, padx=14, sticky="e")

    # =========================================================================
    # TAB 1: LIVE RADAR MONITOR
    # =========================================================================
    def _build_tab_monitor(self):
        tab = self.tab_monitor
        tab.grid_columnconfigure(0, weight=4)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Left: Video Monitor Viewport & Metric Cards
        left_box = ctk.CTkFrame(tab, corner_radius=10, fg_color="#18181B")
        left_box.grid(row=0, column=0, padx=(8, 4), pady=6, sticky="nsew")
        left_box.grid_rowconfigure(0, weight=1)
        left_box.grid_rowconfigure(1, weight=0)
        left_box.grid_columnconfigure(0, weight=1)

        self.video_canvas = ctk.CTkLabel(
            left_box,
            text="Initializing High-Speed Neural Inference Stream...",
            font=ctk.CTkFont(size=15),
            fg_color="#09090B",
            corner_radius=8
        )
        self.video_canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Metric Cards Strip
        metrics_bar = ctk.CTkFrame(left_box, fg_color="#202024", corner_radius=8)
        metrics_bar.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        metrics_bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.card_vehicles = self._create_metric_card(metrics_bar, 0, "TOTAL VEHICLES", "0", "#00E5FF")
        self.card_violations = self._create_metric_card(metrics_bar, 1, "VIOLATIONS", "0", "#FF3D00")
        self.card_avg_speed = self._create_metric_card(metrics_bar, 2, "AVG SPEED", "0.0 km/h", "#FFD600")
        self.card_max_speed = self._create_metric_card(metrics_bar, 3, "MAX SPEED", "0.0 km/h", "#FF1744")
        self.card_fps = self._create_metric_card(metrics_bar, 4, "INFERENCE FPS", "30.0", "#00E676")

        # Right: Quick Sidebar Controls & Live Infractions List
        right_box = ctk.CTkScrollableFrame(tab, corner_radius=10, fg_color="#18181B", width=330)
        right_box.grid(row=0, column=1, padx=(4, 8), pady=6, sticky="nsew")

        # Section: Live Radar Parameters
        ctk.CTkLabel(right_box, text="⚡ LIVE RADAR CONTROLS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E5FF").pack(anchor="w", padx=6, pady=(8, 4))

        # Speed Limit Slider
        self.lbl_limit_val = ctk.CTkLabel(right_box, text=f"Speed Limit: {self.radar_config.speed_limit_kmh:.0f} km/h", font=ctk.CTkFont(size=13))
        self.lbl_limit_val.pack(anchor="w", padx=6, pady=(6, 0))
        self.slider_speed_limit = ctk.CTkSlider(right_box, from_=20, to=140, number_of_steps=120, command=self._on_limit_change)
        self.slider_speed_limit.set(self.radar_config.speed_limit_kmh)
        self.slider_speed_limit.pack(fill="x", padx=6, pady=(2, 8))

        # Trap Distance Slider
        self.lbl_dist_val = ctk.CTkLabel(right_box, text=f"Trap Distance: {self.radar_config.real_distance_meters:.1f} m", font=ctk.CTkFont(size=13))
        self.lbl_dist_val.pack(anchor="w", padx=6, pady=(4, 0))
        self.slider_distance = ctk.CTkSlider(right_box, from_=5, to=80, number_of_steps=75, command=self._on_dist_change)
        self.slider_distance.set(self.radar_config.real_distance_meters)
        self.slider_distance.pack(fill="x", padx=6, pady=(2, 8))

        # Gate 1 & Gate 2 Sliders
        self.lbl_gate1_val = ctk.CTkLabel(right_box, text=f"Gate 1 Entry: {int(self.radar_config.line1_y_ratio*100)}%", font=ctk.CTkFont(size=13))
        self.lbl_gate1_val.pack(anchor="w", padx=6, pady=(4, 0))
        self.slider_gate1 = ctk.CTkSlider(right_box, from_=0.10, to=0.90, number_of_steps=80, command=self._on_gate1_change)
        self.slider_gate1.set(self.radar_config.line1_y_ratio)
        self.slider_gate1.pack(fill="x", padx=6, pady=(2, 8))

        self.lbl_gate2_val = ctk.CTkLabel(right_box, text=f"Gate 2 Exit: {int(self.radar_config.line2_y_ratio*100)}%", font=ctk.CTkFont(size=13))
        self.lbl_gate2_val.pack(anchor="w", padx=6, pady=(4, 0))
        self.slider_gate2 = ctk.CTkSlider(right_box, from_=0.10, to=0.95, number_of_steps=85, command=self._on_gate2_change)
        self.slider_gate2.set(self.radar_config.line2_y_ratio)
        self.slider_gate2.pack(fill="x", padx=6, pady=(2, 12))

        # Quick Actions
        ctk.CTkLabel(right_box, text="📁 WORKSPACE & AUDIT", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E5FF").pack(anchor="w", padx=6, pady=(8, 4))
        actions_row = ctk.CTkFrame(right_box, fg_color="transparent")
        actions_row.pack(fill="x", padx=6, pady=4)

        btn_snaps = ctk.CTkButton(actions_row, text="📸 Snapshots", width=120, command=self._open_snapshots_dir)
        btn_snaps.pack(side="left", padx=(0, 4), expand=True, fill="x")

        btn_csv = ctk.CTkButton(actions_row, text="📊 CSV Log", width=120, command=self._open_csv_log)
        btn_csv.pack(side="right", padx=(4, 0), expand=True, fill="x")

        # Section: Live Infraction Ticker
        ctk.CTkLabel(right_box, text="🚨 LIVE SPEED INFRACTIONS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF3D00").pack(anchor="w", padx=6, pady=(16, 4))

        self.live_violations_box = ctk.CTkTextbox(right_box, height=220, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#101012")
        self.live_violations_box.pack(fill="both", expand=True, padx=6, pady=4)
        self.live_violations_box.insert("0.0", "Radar initialized. Active speed enforcement listening...\n")
        self.live_violations_box.configure(state="disabled")

    def _create_metric_card(self, parent, col, title, initial_val, color):
        card = ctk.CTkFrame(parent, fg_color="#18181B", corner_radius=6)
        card.grid(row=0, column=col, padx=5, pady=6, sticky="nsew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#71717A")
        lbl_t.pack(pady=(6, 0))

        lbl_v = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=18, weight="bold"), text_color=color)
        lbl_v.pack(pady=(0, 6))
        return lbl_v

    # =========================================================================
    # TAB 2: VIOLATIONS & EVIDENCE GALLERY
    # =========================================================================
    def _build_tab_violations(self):
        tab = self.tab_violations
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        # Left: Windows Treeview Table
        table_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#18181B")
        table_frame.grid(row=0, column=0, padx=(8, 4), pady=6, sticky="nsew")
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        tbl_header = ctk.CTkFrame(table_frame, fg_color="transparent")
        tbl_header.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")

        ctk.CTkLabel(tbl_header, text="📋 RECORDED SPEED INFRACTIONS AUDIT", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E5FF").pack(side="left")

        refresh_btn = ctk.CTkButton(tbl_header, text="🔄 Reload Table", width=100, height=28, command=self._reload_violations_table)
        refresh_btn.pack(side="right")

        # Treeview Container
        tree_container = tk.Frame(table_frame, bg="#18181B")
        tree_container.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

        columns = ("Time", "ID", "Class", "Speed", "Limit", "Status", "Direction")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("Time", text="Timestamp")
        self.tree.heading("ID", text="Vehicle ID")
        self.tree.heading("Class", text="Classification")
        self.tree.heading("Speed", text="Recorded Speed")
        self.tree.heading("Limit", text="Speed Limit")
        self.tree.heading("Status", text="Infraction Status")
        self.tree.heading("Direction", text="Traffic Flow")

        self.tree.column("Time", width=120, anchor="center")
        self.tree.column("ID", width=70, anchor="center")
        self.tree.column("Class", width=90, anchor="center")
        self.tree.column("Speed", width=100, anchor="center")
        self.tree.column("Limit", width=85, anchor="center")
        self.tree.column("Status", width=100, anchor="center")
        self.tree.column("Direction", width=95, anchor="center")

        tree_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_row_select)

        # Right: Forensic Snapshot Evidence Viewer
        evidence_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#18181B")
        evidence_frame.grid(row=0, column=1, padx=(4, 8), pady=6, sticky="nsew")
        evidence_frame.grid_rowconfigure(1, weight=1)
        evidence_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(evidence_frame, text="📸 FORENSIC VEHICLE EVIDENCE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF3D00").grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self.evidence_image_lbl = ctk.CTkLabel(
            evidence_frame,
            text="Select an infraction row in the audit table\nto inspect the forensic snapshot.",
            font=ctk.CTkFont(size=13),
            fg_color="#09090B",
            corner_radius=8
        )
        self.evidence_image_lbl.grid(row=1, column=0, padx=12, pady=6, sticky="nsew")

        # Snapshot details box
        self.evidence_details_lbl = ctk.CTkLabel(
            evidence_frame,
            text="No Evidence Selected",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#A1A1AA"
        )
        self.evidence_details_lbl.grid(row=2, column=0, padx=12, pady=6, sticky="ew")

        ev_btn_row = ctk.CTkFrame(evidence_frame, fg_color="transparent")
        ev_btn_row.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")

        open_snap_btn = ctk.CTkButton(ev_btn_row, text="Open in Photos", command=self._open_selected_snapshot_file)
        open_snap_btn.pack(side="left", padx=(0, 4), expand=True, fill="x")

        open_folder_btn = ctk.CTkButton(ev_btn_row, text="Open Folder", command=self._open_snapshots_dir)
        open_folder_btn.pack(side="right", padx=(4, 0), expand=True, fill="x")

    def _style_treeview(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#18181B",
            foreground="#E4E4E7",
            fieldbackground="#18181B",
            rowheight=28,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background="#27272A",
            foreground="#00E5FF",
            font=("Segoe UI", 10, "bold"),
            relief="flat"
        )
        style.map("Treeview", background=[("selected", "#0078D4")], foreground=[("selected", "#FFFFFF")])
        style.map("Treeview.Heading", background=[("active", "#3F3F46")])

    # =========================================================================
    # TAB 3: CALIBRATION & RADAR CONFIGURATION
    # =========================================================================
    def _build_tab_settings(self):
        tab = self.tab_settings
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Left Column: Neural Model & Thresholds
        col1 = ctk.CTkFrame(tab, corner_radius=10, fg_color="#18181B")
        col1.grid(row=0, column=0, padx=(8, 6), pady=8, sticky="nsew")

        ctk.CTkLabel(col1, text="🧠 NEURAL DETECTION & TRACKER", font=ctk.CTkFont(size=15, weight="bold"), text_color="#00E5FF").pack(anchor="w", padx=14, pady=(14, 8))

        ctk.CTkLabel(col1, text="YOLOv8 Model Architecture:", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=14, pady=(6, 2))
        self.model_combo = ctk.CTkComboBox(col1, values=["yolov8n.pt (Fastest - Nano)", "yolov8s.pt (Balanced - Small)", "yolov8m.pt (Accurate - Medium)"], command=self._on_model_change)
        self.model_combo.set("yolov8n.pt (Fastest - Nano)")
        self.model_combo.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(col1, text="Detection Confidence Threshold:", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=14, pady=(6, 2))
        self.lbl_conf_val = ctk.CTkLabel(col1, text=f"Threshold: {self.radar_config.confidence_thresh:.2f}", font=ctk.CTkFont(size=12), text_color="#A1A1AA")
        self.lbl_conf_val.pack(anchor="w", padx=14)
        self.slider_conf = ctk.CTkSlider(col1, from_=0.15, to=0.85, number_of_steps=70, command=self._on_conf_change)
        self.slider_conf.set(self.radar_config.confidence_thresh)
        self.slider_conf.pack(fill="x", padx=14, pady=(0, 16))

        ctk.CTkLabel(col1, text="Speed Measurement Unit:", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=14, pady=(6, 2))
        self.unit_seg = ctk.CTkSegmentedButton(col1, values=["Kilometers / Hour (km/h)", "Miles / Hour (mph)"], command=self._on_unit_change)
        self.unit_seg.set("Kilometers / Hour (km/h)")
        self.unit_seg.pack(fill="x", padx=14, pady=(0, 16))

        # Target Vehicle Classes
        ctk.CTkLabel(col1, text="Target Enforcement Vehicle Classes:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(8, 6))

        self.cls_car_var = ctk.BooleanVar(value=True)
        self.cls_moto_var = ctk.BooleanVar(value=True)
        self.cls_bus_var = ctk.BooleanVar(value=True)
        self.cls_truck_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(col1, text="Passenger Cars (COCO ID 2)", variable=self.cls_car_var, command=self._update_classes).pack(anchor="w", padx=20, pady=3)
        ctk.CTkCheckBox(col1, text="Motorcycles & Scooters (COCO ID 3)", variable=self.cls_moto_var, command=self._update_classes).pack(anchor="w", padx=20, pady=3)
        ctk.CTkCheckBox(col1, text="Buses (COCO ID 5)", variable=self.cls_bus_var, command=self._update_classes).pack(anchor="w", padx=20, pady=3)
        ctk.CTkCheckBox(col1, text="Commercial Trucks (COCO ID 7)", variable=self.cls_truck_var, command=self._update_classes).pack(anchor="w", padx=20, pady=3)

        # Right Column: Visual Overlays & Road Geometry
        col2 = ctk.CTkFrame(tab, corner_radius=10, fg_color="#18181B")
        col2.grid(row=0, column=1, padx=(6, 8), pady=8, sticky="nsew")

        ctk.CTkLabel(col2, text="📐 ROAD GEOMETRY & OVERLAYS", font=ctk.CTkFont(size=15, weight="bold"), text_color="#00E5FF").pack(anchor="w", padx=14, pady=(14, 8))

        ctk.CTkLabel(col2, text="Display & Overlay Elements:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(6, 6))

        self.chk_hud = ctk.CTkCheckBox(col2, text="Display Sci-Fi Radar Dashboard HUD", variable=self.menu_show_hud, command=self._on_view_toggle)
        self.chk_hud.pack(anchor="w", padx=20, pady=4)

        self.chk_badges = ctk.CTkCheckBox(col2, text="Display Floating Speed & Class Badges", variable=self.menu_show_badges, command=self._on_view_toggle)
        self.chk_badges.pack(anchor="w", padx=20, pady=4)

        self.chk_trails = ctk.CTkCheckBox(col2, text="Display Motion Trajectory Trails", variable=self.menu_show_trails, command=self._on_view_toggle)
        self.chk_trails.pack(anchor="w", padx=20, pady=4)

        # Video Recording
        ctk.CTkLabel(col2, text="Audit Recording & Storage:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(16, 6))
        self.save_video_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(col2, text="Record Full Annotated Radar Surveillance Stream", variable=self.save_video_var).pack(anchor="w", padx=20, pady=4)

        # Visual Calibrator Launcher Button
        calib_banner = ctk.CTkFrame(col2, fg_color="#27272A", corner_radius=8)
        calib_banner.pack(fill="x", padx=14, pady=(24, 10))

        ctk.CTkLabel(calib_banner, text="Visual Line & Homography Calibrator", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00E5FF").pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(calib_banner, text="Click directly on roadway video to position entry/exit gates or 4-corner road perspective quads.", font=ctk.CTkFont(size=11), text_color="#A1A1AA", wraplength=400).pack(anchor="w", padx=12, pady=(0, 8))

        calib_launch_btn = ctk.CTkButton(calib_banner, text="🎯 Open Visual Calibration Window", fg_color="#0078D4", hover_color="#0063B1", command=self._launch_calibrator)
        calib_launch_btn.pack(fill="x", padx=12, pady=(0, 10))

    # =========================================================================
    # EVENT HANDLERS & LOGIC
    # =========================================================================
    def _on_limit_change(self, val):
        self.radar_config.speed_limit_kmh = float(val)
        unit = self.radar_config.get_unit_label()
        disp_limit = self.radar_config.speed_limit_kmh * self.radar_config.get_unit_multiplier()
        self.lbl_limit_val.configure(text=f"Speed Limit: {disp_limit:.0f} {unit}")

    def _on_dist_change(self, val):
        self.radar_config.real_distance_meters = float(val)
        self.lbl_dist_val.configure(text=f"Trap Distance: {val:.1f} m")
        if self.radar_engine and hasattr(self.radar_engine.speed_estimator, "distance_meters"):
            self.radar_engine.speed_estimator.distance_meters = float(val)

    def _on_gate1_change(self, val):
        self.radar_config.line1_y_ratio = float(val)
        self.lbl_gate1_val.configure(text=f"Gate 1 Entry: {int(val*100)}%")
        if self.radar_engine and hasattr(self.radar_engine.speed_estimator, "line1_y"):
            self.radar_engine.speed_estimator.line1_y = int(val * self.radar_engine.frame_height)

    def _on_gate2_change(self, val):
        self.radar_config.line2_y_ratio = float(val)
        self.lbl_gate2_val.configure(text=f"Gate 2 Exit: {int(val*100)}%")
        if self.radar_engine and hasattr(self.radar_engine.speed_estimator, "line2_y"):
            self.radar_engine.speed_estimator.line2_y = int(val * self.radar_engine.frame_height)

    def _on_conf_change(self, val):
        self.radar_config.confidence_thresh = float(val)
        self.lbl_conf_val.configure(text=f"Threshold: {val:.2f}")
        if self.radar_engine:
            self.radar_engine.config.confidence_thresh = float(val)

    def _on_unit_change(self, val):
        self.radar_config.speed_unit = "km/h" if "km/h" in val else "mph"
        self._on_limit_change(self.slider_speed_limit.get())

    def _update_classes(self):
        classes = []
        if self.cls_car_var.get(): classes.append(2)
        if self.cls_moto_var.get(): classes.append(3)
        if self.cls_bus_var.get(): classes.append(5)
        if self.cls_truck_var.get(): classes.append(7)
        self.radar_config.target_classes = classes
        if self.radar_engine:
            self.radar_engine.config.target_classes = classes

    def _on_view_toggle(self):
        self.radar_config.show_radar_hud = self.menu_show_hud.get()
        self.radar_config.show_speed_badges = self.menu_show_badges.get()
        self.radar_config.show_trajectories = self.menu_show_trails.get()

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv"), ("All files", "*.*")]
        )
        if file_path:
            self._set_source(file_path)

    def _set_source(self, src: str):
        self.selected_source = src
        display_name = "Live Webcam (0)" if src == "0" else Path(src).name
        self.source_label.configure(text=display_name)
        if self.is_processing:
            self._stop_monitoring()
            self.after(300, self._start_monitoring)

    def _toggle_monitoring(self):
        if self.is_processing:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        if self.is_processing:
            return

        self.is_processing = True
        self.is_paused = False
        self.btn_start.configure(text="■ Stop Radar", fg_color="#D50000", hover_color="#9B0000")
        self.btn_pause.configure(state="normal", text="⏸ Pause")
        self.status_pill.configure(text="● RADAR ACTIVE", text_color="#00E676")
        self.sb_status.configure(text=f"Status: Monitoring {Path(str(self.selected_source)).name}")

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _stop_monitoring(self):
        self.is_processing = False
        if self.radar_engine:
            self.radar_engine.is_running = False
        self.btn_start.configure(text="▶ Start Radar", fg_color="#00C853", hover_color="#009624")
        self.btn_pause.configure(state="disabled", text="⏸ Pause")
        self.status_pill.configure(text="● SYSTEM STANDBY", text_color="#A1A1AA")
        self.sb_status.configure(text="Status: System Standby")

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.configure(text="▶ Resume")
            self.status_pill.configure(text="● RADAR PAUSED", text_color="#FFD600")
            self.sb_status.configure(text="Status: Paused by user")
        else:
            self.btn_pause.configure(text="⏸ Pause")
            self.status_pill.configure(text="● RADAR ACTIVE", text_color="#00E676")
            self.sb_status.configure(text="Status: Monitoring Live Stream")

    def _reset_counters(self):
        if self.radar_engine:
            self.radar_engine.violation_manager.total_measured = 0
            self.radar_engine.violation_manager.total_violations = 0
            self.radar_engine.violation_manager.max_speed = 0.0
            self.radar_engine.violation_manager.speed_sum = 0.0
            self.radar_engine.violation_manager.logged_ids.clear()
            self.radar_engine.violation_manager.recent_violations.clear()
        self.card_vehicles.configure(text="0")
        self.card_violations.configure(text="0")
        self.card_avg_speed.configure(text="0.0")
        self.card_max_speed.configure(text="0.0")

    def _on_model_change(self, choice):
        model_map = {
            "yolov8n.pt (Fastest - Nano)": "yolov8n.pt",
            "yolov8s.pt (Balanced - Small)": "yolov8s.pt",
            "yolov8m.pt (Accurate - Medium)": "yolov8m.pt"
        }
        self.radar_config.model_name = model_map.get(choice, "yolov8n.pt")
        if self.is_processing:
            self._stop_monitoring()
            self.after(400, self._start_monitoring)

    def _launch_calibrator(self):
        src = self.selected_source
        subprocess.Popen([sys.executable, "calibrate_tool.py", "--source", str(src)])

    def _save_frame_snapshot(self):
        if self.active_frame_raw is not None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            out_file = Path("output/violations") / f"manual_snapshot_{ts}.jpg"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_file), self.active_frame_raw)
            messagebox.showinfo("Snapshot Saved", f"Frame snapshot saved successfully:\n{out_file}")

    def _open_snapshots_dir(self):
        path = os.path.abspath("output/violations")
        os.makedirs(path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])

    def _open_csv_log(self):
        path = os.path.abspath("output/logs/traffic_speed_log.csv")
        if os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        else:
            messagebox.showinfo("Log", "No speed audit log recorded yet.")

    def _open_output_dir(self):
        path = os.path.abspath("output")
        os.makedirs(path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)

    def _show_diagnostics(self):
        cuda_ok = cv2.cuda.getCudaEnabledDeviceCount() > 0 or ("torch" in sys.modules)
        info = f"Python Version: {sys.version}\n" \
               f"Platform: {sys.platform}\n" \
               f"CUDA Hardware Acceleration: {'Active (Device 0)' if cuda_ok else 'CPU'}\n" \
               f"YOLOv8 Engine: Ultralytics Loaded\n" \
               f"Tracker: ByteTrack + CentroidTracker Fallback"
        messagebox.showinfo("System Diagnostics", info)

    def _show_about(self):
        messagebox.showinfo("About", "AI Traffic Speed Radar Workstation v2.0\nPowered by YOLOv8, ByteTrack & Computer Vision\nReal-time Speed Trap Enforcement & Automated Snapshot Capture.")

    def _on_exit(self):
        self._stop_monitoring()
        self.destroy()

    # =========================================================================
    # WORKER THREAD & VIDEO STREAM LOOP
    # =========================================================================
    def _worker_loop(self):
        try:
            self.radar_engine = TrafficSpeedRadar(self.radar_config)
            source = self.selected_source
            video_src = int(source) if str(source).isdigit() else source
            cap = cv2.VideoCapture(video_src)

            if not cap.isOpened():
                print(f"[Worker] Could not open video source: {source}")
                self.is_processing = False
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or np.isnan(fps):
                fps = 30.0

            self.radar_engine.init_estimator(width, height, fps)

            save_writer = None
            if self.save_video_var.get():
                out_path = Path("output/radar_recording.mp4")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                save_writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

            frame_idx = 0
            while self.is_processing and cap.isOpened():
                if self.is_paused:
                    time.sleep(0.05)
                    continue

                ret, frame = cap.read()
                if not ret:
                    if not str(source).isdigit():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    if not ret:
                        break

                frame_idx += 1
                timestamp = frame_idx / fps

                annotated = self.radar_engine.process_frame(frame, frame_idx, timestamp)
                self.active_frame_raw = annotated

                if save_writer is not None:
                    save_writer.write(annotated)

                if not self.frame_queue.full():
                    self.frame_queue.put(annotated)

            cap.release()
            if save_writer is not None:
                save_writer.release()

        except Exception as e:
            print(f"[Worker Exception]: {e}")
        finally:
            self.is_processing = False

    # =========================================================================
    # GUI REFRESH LOOP & AUDIT TABLE
    # =========================================================================
    def _update_gui_loop(self):
        try:
            # Video Frame Refresh
            if not self.frame_queue.empty():
                frame = self.frame_queue.get_nowait()
                h, w = frame.shape[:2]

                canv_w = max(self.video_canvas.winfo_width(), 640)
                canv_h = max(self.video_canvas.winfo_height(), 360)

                scale = min(canv_w / w, canv_h / h)
                new_w = max(int(w * scale), 320)
                new_h = max(int(h * scale), 180)

                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(new_w, new_h))
                self.video_canvas.configure(image=ctk_img, text="")

            # Metrics and Telemetry
            if self.radar_engine:
                vm = self.radar_engine.violation_manager
                unit = self.radar_config.get_unit_label()
                mult = self.radar_config.get_unit_multiplier()

                self.card_vehicles.configure(text=str(vm.total_measured))
                self.card_violations.configure(text=str(vm.total_violations))
                self.card_avg_speed.configure(text=f"{vm.average_speed * mult:.1f} {unit}")
                self.card_max_speed.configure(text=f"{vm.max_speed * mult:.1f} {unit}")
                self.card_fps.configure(text=f"{self.radar_engine.visualizer.fps_tracker.tick():.1f}")

                self.sb_metrics.configure(text=f"Violations: {vm.total_violations} | Measured: {vm.total_measured}")

                # Update live violations ticker
                if vm.recent_violations:
                    text_content = ""
                    for v in vm.recent_violations[:10]:
                        text_content += f"[{v['timestamp'][-8:]}] #{v['vehicle_id']} {v['class'].upper()} @ {v['speed']} {v['unit']} (LIMIT {v['speed_limit']})\n"
                    self.live_violations_box.configure(state="normal")
                    self.live_violations_box.delete("0.0", "end")
                    self.live_violations_box.insert("0.0", text_content)
                    self.live_violations_box.configure(state="disabled")

            if not self.is_processing and self.worker_thread is not None and not self.worker_thread.is_alive():
                self._stop_monitoring()
                self.worker_thread = None

        except Exception:
            pass

        self.after(25, self._update_gui_loop)

    def _reload_violations_table(self):
        """Reads CSV audit log and populates Windows Treeview."""
        csv_file = Path("output/logs/traffic_speed_log.csv")
        if not csv_file.exists():
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            import csv
            with open(csv_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for item in reader:
                    vals = (
                        item.get("Timestamp", "")[-8:],
                        f"#{item.get('Vehicle_ID', '')}",
                        item.get("Class", "").upper(),
                        f"{item.get('Speed', '')} {item.get('Unit', '')}",
                        f"{item.get('Speed_Limit', '')} {item.get('Unit', '')}",
                        item.get("Status", ""),
                        item.get("Direction", "")
                    )
                    row_id = self.tree.insert("", "end", values=vals)
                    snap_path = item.get("Snapshot_Path", "")
                    self.tree.set(row_id, "Snapshot", snap_path)
        except Exception as e:
            print(f"[Treeview] Error reloading CSV: {e}")

    def _on_tree_row_select(self, event):
        """When an audit row is clicked, display forensic vehicle snapshot in preview pane."""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        vals = item.get("values", [])
        if not vals:
            return

        time_val, veh_id, cls, speed, limit, status, direction = vals

        # Look for matching snapshot file
        snaps_dir = Path("output/violations")
        clean_id = veh_id.replace("#", "")
        matching = list(snaps_dir.glob(f"violation_id{clean_id}_*.jpg"))

        if matching:
            snap_file = matching[0]
            self.selected_snapshot_path = str(snap_file)
            try:
                img = Image.open(str(snap_file))
                # Scale for preview box
                pw, ph = 360, 240
                img.thumbnail((pw, ph), Image.Resampling.LANCZOS)
                preview_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.evidence_image_lbl.configure(image=preview_ctk, text="")
                self.evidence_details_lbl.configure(text=f"ID: {veh_id} | Class: {cls} | Speed: {speed}\nRecorded at {time_val} ({direction})")
            except Exception as e:
                self.evidence_image_lbl.configure(image=None, text=f"Error loading image: {e}")
        else:
            self.selected_snapshot_path = None
            self.evidence_image_lbl.configure(image=None, text="Snapshot not found on disk.")
            self.evidence_details_lbl.configure(text=f"ID: {veh_id} | Class: {cls} | Speed: {speed}")

    def _open_selected_snapshot_file(self):
        if self.selected_snapshot_path and os.path.exists(self.selected_snapshot_path):
            if sys.platform == "win32":
                os.startfile(self.selected_snapshot_path)
        else:
            messagebox.showinfo("Notice", "Please select an infraction from the table first.")


if __name__ == "__main__":
    app = WindowsSpeedRadarApp()
    app.mainloop()
