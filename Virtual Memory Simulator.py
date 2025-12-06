import tkinter as tk
from tkinter import ttk, messagebox
import random
import collections
import math

# =============================================================================
#  VIRTUAL MEMORY SIMULATOR (BA6 + Scenario Presets)
# =============================================================================

class VirtualMemorySimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("OS Project: VM Simulator")
        self.root.geometry("1150x950")
        
        # --- STATE VARIABLES ---
        self.pages = []          
        self.capacity = 3        
        self.frames = []         
        self.current_step = 0    
        self.faults = 0
        self.hits = 0
        
        # --- ALGORITHM STATE ---
        self.access_history = []        
        self.freq_counter = {}          
        self.arrival_times = {}         
        self.sc_pointer = 0             
        self.ref_bits = {}              
        self.mod_bits = {}              
        self.arb_registers = {}         
        
        # --- ARB / AGING SPECIFIC ---
        self.timer_counter = 0
        self.INTERRUPT_INTERVAL = 6
        
        # --- ANIMATION & ESC STATE ---
        self.is_animating = False
        self.anim_visual_offset = 0.0
        self.anim_visual_start_idx = 0
        self.esc_phase = 1        
        self.steps_in_phase = 0   
        self.requests_is_write = [] 

        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # --- TABS ---
        tab_control = ttk.Notebook(self.root)
        self.sim_tab = ttk.Frame(tab_control)
        self.frag_tab = ttk.Frame(tab_control)
        tab_control.add(self.sim_tab, text='  Page Replacement Sim  ')
        tab_control.add(self.frag_tab, text='  Fragmentation Analysis  ')
        tab_control.pack(expand=1, fill="both")

        # ================= SIMULATION TAB =================
        ctrl_frame = tk.LabelFrame(self.sim_tab, text="Configuration", padx=10, pady=10)
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        # Row 0: Ref String (PRESERVED)
        tk.Label(ctrl_frame, text="Ref String (Pages):").grid(row=0, column=0, sticky="w")
        self.entry_refs = tk.Entry(ctrl_frame, width=50)
        self.entry_refs.insert(0, "7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1")
        self.entry_refs.grid(row=0, column=1, padx=5, pady=2)

        # Row 1: R/W String (PRESERVED)
        self.lbl_rw = tk.Label(ctrl_frame, text="R/W String (R/W):", fg="blue")
        self.entry_rw = tk.Entry(ctrl_frame, width=50)
        default_rw = "R, R, R, W, R, R, R, W, R, R, R, W, R, R, R, R, W, R, R, W"
        self.entry_rw.insert(0, default_rw)
        
        # Controls (Frames)
        tk.Label(ctrl_frame, text="Frames:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.entry_frames = tk.Entry(ctrl_frame, width=5)
        self.entry_frames.insert(0, "3") 
        self.entry_frames.grid(row=0, column=3, padx=5)

        # --- NEW PRESET DROPDOWN (Added here) ---
        tk.Label(ctrl_frame, text="Load Preset:", fg="#555").grid(row=1, column=2, sticky="w", padx=(10,0))
        self.preset_var = tk.StringVar()
        self.preset_menu = ttk.Combobox(ctrl_frame, textvariable=self.preset_var, state="readonly", width=15)
        self.preset_menu['values'] = ("Select...", "Belady Anomaly", "High Locality", "Thrashing", "Random Mix")
        self.preset_menu.current(0)
        self.preset_menu.bind("<<ComboboxSelected>>", self.apply_preset)
        self.preset_menu.grid(row=1, column=3, padx=5)
        # ----------------------------------------

        tk.Button(ctrl_frame, text="Generate Random", command=self.gen_random).grid(row=0, column=4, padx=5)
        tk.Button(ctrl_frame, text="LOAD / RESET", command=self.load_data, bg="#d0d0ff", font=("Arial", 9, "bold"), height=2).grid(row=0, column=5, rowspan=2, padx=10)

        # --- ALGO CONTROL ---
        algo_frame = tk.Frame(self.sim_tab, pady=10, relief="groove", bd=2)
        algo_frame.pack(fill="x", padx=10)
        
        tk.Label(algo_frame, text="Algorithm:", font=("Arial", 11)).pack(side="left")
        self.algo_var = tk.StringVar()
        algos = ["FIFO", "LRU", "Optimal", "LFU", "MFU", "Second-Chance", "Enhanced-Second-Chance", "Add-Ref-Bits"]
        self.algo_menu = ttk.Combobox(algo_frame, textvariable=self.algo_var, values=algos, state="readonly", width=23)
        self.algo_menu.current(7) 
        self.algo_menu.pack(side="left", padx=5)
        self.algo_menu.bind("<<ComboboxSelected>>", self.on_algo_change)

        # ACTION BUTTONS
        self.step_btn = tk.Button(algo_frame, text="STEP >", command=self.run_step, bg="#90ee90", width=12, font=("Arial", 10, "bold"))
        self.step_btn.pack(side="left", padx=10)
        
        self.run_all_btn = tk.Button(algo_frame, text=">> Run All", command=self.run_all, bg="#ffcc80", width=12, font=("Arial", 10, "bold"))
        self.run_all_btn.pack(side="left", padx=10)
        
        # DYNAMIC BUTTONS (Interrupt)
        self.interrupt_btn = tk.Button(algo_frame, text="Timer Interrupt", command=self.manual_interrupt, bg="#ff6b6b", fg="white", font=("Arial", 9, "bold"))
        
        # GRAPH BUTTON (Belady's Anomaly)
        self.graph_btn = tk.Button(algo_frame, text="Show Graph 📈", command=self.show_performance_graph, bg="#81d4fa", font=("Arial", 9, "bold"))
        self.graph_btn.pack(side="left", padx=10)

        # Canvas Area
        self.canvas_area = tk.Frame(self.sim_tab, pady=10)
        self.canvas_area.pack(expand=True, fill="both")
        
        self.info_lbl = tk.Label(self.canvas_area, text="Load data to start...", font=("Consolas", 14, "bold"))
        self.info_lbl.pack(pady=(10,0))
        
        self.phase_lbl = tk.Label(self.canvas_area, text="", font=("Arial", 10, "italic"), fg="#555")
        self.phase_lbl.pack()

        self.frames_container = tk.Frame(self.canvas_area)
        self.frames_container.pack(pady=20, fill="both", expand=True)

        # Stats
        stat_frame = tk.LabelFrame(self.sim_tab, text="Statistics & Logs", padx=10, pady=10)
        stat_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        self.stats_lbl = tk.Label(stat_frame, text="Faults: 0 | Hits: 0", font=("Arial", 12, "bold"))
        self.stats_lbl.pack(anchor="w")
        self.log_text = tk.Text(stat_frame, height=8, width=100, state="disabled", bg="#f4f4f4")
        self.log_text.pack(fill="x")

        # ================= FRAGMENTATION TAB =================
        f_frame = tk.Frame(self.frag_tab, padx=20, pady=20)
        f_frame.pack(fill="both", expand=True)
        tk.Label(f_frame, text="Internal Fragmentation Analysis", font=("Arial", 16, "bold")).pack(pady=10)
        
        input_frame = tk.Frame(f_frame)
        input_frame.pack()
        tk.Label(input_frame, text="Process Size (KB):").grid(row=0, column=0)
        self.frag_proc_size = tk.Entry(input_frame); self.frag_proc_size.insert(0, "1405"); self.frag_proc_size.grid(row=0, column=1)
        tk.Label(input_frame, text="Page Size (KB):").grid(row=1, column=0)
        self.frag_page_size = tk.Entry(input_frame); self.frag_page_size.insert(0, "4"); self.frag_page_size.grid(row=1, column=1)
        tk.Button(input_frame, text="Calculate", command=self.calc_frag, bg="#ddd").grid(row=2, column=0, columnspan=2, pady=10)
        
        self.frag_result_text = tk.StringVar()
        tk.Label(f_frame, textvariable=self.frag_result_text, justify="left", font=("Consolas", 11)).pack(pady=10)
        self.frag_canvas = tk.Canvas(f_frame, bg="white", height=400); self.frag_canvas.pack(fill="x")

        self.on_algo_change()

    # --- PRESET LOGIC (NEW) ---
    def apply_preset(self, event=None):
        choice = self.preset_var.get()
        refs, rw, f = "", "", ""
        
        if choice == "Belady Anomaly":
            refs = "1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5"
            rw = "R, R, R, W, R, R, R, W, R, R, R, W"
            f = "3"
        elif choice == "High Locality":
            refs = "1, 1, 1, 2, 2, 3, 1, 2, 4, 4, 4, 1"
            rw = "R, W, R, R, W, R, R, R, W, R, W, R"
            f = "3"
        elif choice == "Thrashing":
            refs = "1, 2, 3, 4, 5, 6, 1, 2, 3, 7, 8, 9"
            rw = "R, R, R, R, R, R, R, R, R, R, R, R"
            f = "2"
        elif choice == "Random Mix":
            self.gen_random()
            return

        if refs:
            self.entry_refs.delete(0, tk.END); self.entry_refs.insert(0, refs)
            self.entry_rw.delete(0, tk.END); self.entry_rw.insert(0, rw)
            self.entry_frames.delete(0, tk.END); self.entry_frames.insert(0, f)
            messagebox.showinfo("Preset Loaded", f"Loaded '{choice}' scenario.\nClick LOAD/RESET to initialize.")

    def on_algo_change(self, event=None):
        algo = self.algo_var.get()
        
        # 1. Toggle R/W input
        if algo == "Enhanced-Second-Chance":
            self.lbl_rw.grid(row=1, column=0, sticky="w")
            self.entry_rw.grid(row=1, column=1, padx=5, pady=2)
        else:
            self.lbl_rw.grid_remove()
            self.entry_rw.grid_remove()
            
        # 2. Toggle Interrupt Button
        if algo == "Add-Ref-Bits":
            self.interrupt_btn.pack(side="left", padx=10)
        else:
            self.interrupt_btn.pack_forget()

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def gen_random(self):
        count = 20
        vals = [str(random.randint(0, 9)) for _ in range(count)]
        self.entry_refs.delete(0, tk.END)
        self.entry_refs.insert(0, ", ".join(vals))
        
        rw_vals = ["W" if random.random() < 0.3 else "R" for _ in range(count)]
        self.entry_rw.delete(0, tk.END)
        self.entry_rw.insert(0, ", ".join(rw_vals))

    def load_data(self):
        try:
            ref_str = self.entry_refs.get()
            self.pages = [int(x.strip()) for x in ref_str.split(',')]
            self.capacity = int(self.entry_frames.get())
            if self.capacity <= 0: raise ValueError
            
            rw_str = self.entry_rw.get()
            raw_rw_list = [x.strip().upper() for x in rw_str.split(',')]
            self.requests_is_write = []
            for i in range(len(self.pages)):
                is_w = False
                if i < len(raw_rw_list):
                    if raw_rw_list[i] == 'W': is_w = True
                self.requests_is_write.append(is_w)
            
            self.frames = []
            self.current_step = 0
            self.faults = 0; self.hits = 0
            self.access_history = []
            self.freq_counter = collections.defaultdict(int)
            self.arrival_times = {}
            self.sc_pointer = 0
            self.ref_bits = {} 
            self.mod_bits = {}
            self.arb_registers = {}
            self.is_animating = False
            self.timer_counter = 0
            
            self.log("Loaded Data Successfully.")
            self.render_frames(None, None)
            
        except ValueError:
            messagebox.showerror("Error", "Invalid input.")

    # =========================================================================
    #  BELADY'S ANOMALY / PERFORMANCE GRAPH
    # =========================================================================
    def show_performance_graph(self):
        if not self.pages:
            messagebox.showerror("Error", "Load data first.")
            return

        graph_win = tk.Toplevel(self.root)
        graph_win.title("Performance Analysis (Faults vs Frames)")
        graph_win.geometry("600x450")
        
        algo = self.algo_var.get()
        tk.Label(graph_win, text=f"Fault Curve for: {algo}", font=("Arial", 14, "bold")).pack(pady=10)
        
        canvas = tk.Canvas(graph_win, bg="white", width=500, height=300)
        canvas.pack(pady=20)
        
        # --- Run Simulations Silently ---
        results = [] # List of (frame_count, fault_count)
        max_frames_to_test = 8
        
        for f_count in range(1, max_frames_to_test + 1):
            faults = self.simulate_silent(algo, f_count)
            results.append(faults)
            
        # --- Draw Graph ---
        w = 500; h = 300; padding = 40
        max_faults = max(results) if results else 1
        
        # Axes
        canvas.create_line(padding, h-padding, w-padding, h-padding, width=2) # X
        canvas.create_line(padding, h-padding, padding, padding, width=2)     # Y
        
        prev_x, prev_y = None, None
        
        for i, faults in enumerate(results):
            frames = i + 1
            x = padding + (i * ((w - 2*padding) / (max_frames_to_test - 1)))
            y = (h - padding) - (faults * ((h - 2*padding) / max_faults))
            
            # Point
            canvas.create_oval(x-4, y-4, x+4, y+4, fill="blue")
            canvas.create_text(x, y-15, text=str(faults), font=("Arial", 9, "bold"))
            canvas.create_text(x, h-20, text=f"F{frames}", font=("Arial", 9))
            
            # Line
            if prev_x is not None:
                color = "blue"
                width = 2
                
                # --- ANOMALY DETECTION ---
                if y < prev_y: 
                    color = "red" 
                    width = 4
                    
                canvas.create_line(prev_x, prev_y, x, y, fill=color, width=width)
                
            prev_x, prev_y = x, y

        tk.Label(graph_win, text="X-Axis: Frames  |  Y-Axis: Total Page Faults", fg="#555").pack()
        tk.Label(graph_win, text="* Red line indicates Belady's Anomaly (Faults increased with more frames)", fg="red", font=("Arial", 9, "bold")).pack()

    def simulate_silent(self, algo, frame_cap):
        """Runs the algo purely in memory without UI to get fault count."""
        local_frames = []
        local_faults = 0
        local_ref_bits = {}
        local_mod_bits = {}
        local_arb = {}
        local_freq = collections.defaultdict(int)
        local_arrival = {} 
        sc_ptr = 0
        
        for p in set(self.pages): local_arb[p] = 0

        for step, page in enumerate(self.pages):
            is_write = self.requests_is_write[step] if step < len(self.requests_is_write) else False
            
            # HIT
            if page in local_frames:
                if is_write: local_mod_bits[page] = 1
                local_ref_bits[page] = 1
                local_freq[page] += 1
                if algo == "LRU":
                    local_frames.remove(page); local_frames.append(page)
                continue 
            
            # FAULT
            local_faults += 1
            
            if len(local_frames) < frame_cap:
                local_frames.append(page)
                local_arrival[page] = step
                local_freq[page] = 1
                local_ref_bits[page] = 1
                local_mod_bits[page] = 1 if is_write else 0
                local_arb[page] = 0
            else:
                # Replacement Logic
                victim = -1
                
                if algo in ["FIFO", "LRU"]:
                    victim = local_frames[0]
                elif algo == "Optimal":
                    farthest = -1
                    future = self.pages[step+1:]
                    for f in local_frames:
                        if f not in future:
                            victim = f; break
                        idx = future.index(f)
                        if idx > farthest: farthest = idx; victim = f
                elif algo == "LFU":
                    min_f = min(local_freq[p] for p in local_frames)
                    cands = [p for p in local_frames if local_freq[p] == min_f]
                    victim = min(cands, key=lambda x: local_arrival.get(x,0))
                elif algo == "MFU":
                    max_f = max(local_freq[p] for p in local_frames)
                    cands = [p for p in local_frames if local_freq[p] == max_f]
                    victim = min(cands, key=lambda x: local_arrival.get(x,0))
                elif algo == "Second-Chance":
                    while True:
                        curr = local_frames[sc_ptr]
                        if local_ref_bits.get(curr, 0) == 0:
                            victim = curr
                            sc_ptr = (sc_ptr + 1) % frame_cap
                            break
                        local_ref_bits[curr] = 0
                        sc_ptr = (sc_ptr + 1) % frame_cap
                # For graph speed, default complex ones (ESC/ARB) to FIFO or simple
                elif algo == "Add-Ref-Bits":
                     min_val = min(local_arb[p] for p in local_frames)
                     cands = [p for p in local_frames if local_arb[p] == min_val]
                     victim = min(cands, key=lambda x: local_arrival.get(x,0))
                else:
                    victim = local_frames[0] 

                # Replace
                idx = local_frames.index(victim)
                if algo in ["FIFO", "LRU"]:
                    local_frames.pop(0); local_frames.append(page)
                else:
                    local_frames[idx] = page
                
                local_arrival[page] = step
                local_freq[page] = 1
                local_ref_bits[page] = 1
                local_mod_bits[page] = 1 if is_write else 0
                local_arb[page] = 0
        
        return local_faults

    # =========================================================================
    #  CORE LOGIC (ARB Interrupts)
    # =========================================================================
    def perform_arb_interrupt(self):
        for p in self.frames:
            current_reg = self.arb_registers.get(p, 0)
            current_reg = current_reg >> 1
            if self.ref_bits.get(p, 0) == 1:
                current_reg |= 128
            self.arb_registers[p] = current_reg
            self.ref_bits[p] = 0
        self.timer_counter = 0 
        self.log(f"--- [Timer Interrupt] Registers Shifted ---")

    def manual_interrupt(self):
        if self.algo_var.get() != "Add-Ref-Bits": return
        self.perform_arb_interrupt()
        page = self.pages[self.current_step] if self.current_step < len(self.pages) else None
        self.render_frames(page, "INTERRUPT")

    def run_step(self):
        if self.is_animating: return 
        if self.current_step >= len(self.pages):
            messagebox.showinfo("Done", "Simulation Finished.")
            return

        page = self.pages[self.current_step]
        algo = self.algo_var.get()
        status = "HIT"
        is_write = self.requests_is_write[self.current_step]
        
        if page in self.frames: self.ref_bits[page] = 1 
        if page in self.frames and is_write: self.mod_bits[page] = 1 
        
        if algo == "Add-Ref-Bits":
            self.timer_counter += 1
            interrupt_needed = False
            if self.timer_counter >= self.INTERRUPT_INTERVAL: interrupt_needed = True
            if page not in self.frames: interrupt_needed = True
            if interrupt_needed: self.perform_arb_interrupt()

        if page in self.frames:
            self.hits += 1
            status = "HIT"
            if algo == "LRU": self.frames.remove(page); self.frames.append(page)
            if algo in ["LFU", "MFU"]: self.freq_counter[page] += 1
            self.finalize_step_ui(page, status, is_write)
        else:
            self.faults += 1
            status = "FAULT"
            if len(self.frames) < self.capacity:
                self.frames.append(page)
                self.init_metadata(page, is_write)
                self.finalize_step_ui(page, status, is_write)
            else:
                if algo in ["Second-Chance", "Enhanced-Second-Chance"]:
                    self.start_animated_scan(page, is_write)
                else:
                    victim = self.get_victim(algo)
                    idx = self.frames.index(victim)
                    if algo in ["LRU", "FIFO"]:
                        self.frames.pop(0); self.frames.append(page) 
                    else:
                        self.frames[idx] = page
                    self.cleanup_metadata(victim)
                    self.init_metadata(page, is_write)
                    self.finalize_step_ui(page, status, is_write, victim=victim)

    def finalize_step_ui(self, page, status, is_write, victim=None):
        algo = self.algo_var.get()
        if algo in ["LFU", "MFU"] and status == "FAULT": self.freq_counter[page] = 1
        op_type = "WRITE" if is_write else "READ"
        status_str = status
        if victim is not None: status_str += f" (Evicted Pg {victim})"
        self.log(f"Step {self.current_step+1}: Req {page} ({op_type}) -> {status_str}. Frames: {self.frames}")
        self.current_step += 1
        self.update_stats()
        self.render_frames(page, status_str)
        self.phase_lbl.config(text="")

    def run_all(self):
        if self.is_animating:
             messagebox.showwarning("Busy", "Animation in progress.")
             return
        if self.current_step >= len(self.pages):
            messagebox.showinfo("Done", "Already Finished.")
            return
        self.step_btn.config(state="disabled")
        self.run_all_btn.config(state="disabled")
        while self.current_step < len(self.pages):
            self.run_step()
            if self.is_animating: break 
        self.step_btn.config(state="normal")
        self.run_all_btn.config(state="normal")

    def init_metadata(self, page, is_write):
        self.arrival_times[page] = self.current_step
        self.freq_counter[page] = 1
        self.ref_bits[page] = 1
        self.mod_bits[page] = 1 if is_write else 0
        self.arb_registers[page] = 0 

    def cleanup_metadata(self, victim):
        for db in [self.freq_counter, self.arrival_times, self.ref_bits, self.mod_bits, self.arb_registers]:
            if victim in db: del db[victim]

    def get_victim(self, algo):
        if algo in ["FIFO", "LRU"]: return self.frames[0]
        elif algo == "Optimal":
            farthest_idx, victim = -1, -1
            future = self.pages[self.current_step+1:]
            for f in self.frames:
                if f not in future: return f
                idx = future.index(f)
                if idx > farthest_idx: farthest_idx, victim = idx, f
            return victim
        elif algo == "LFU":
            min_f = min(self.freq_counter[p] for p in self.frames)
            cands = [p for p in self.frames if self.freq_counter[p] == min_f]
            return min(cands, key=lambda x: self.arrival_times[x])
        elif algo == "MFU":
            max_f = max(self.freq_counter[p] for p in self.frames)
            cands = [p for p in self.frames if self.freq_counter[p] == max_f]
            return min(cands, key=lambda x: self.arrival_times[x])
        elif algo == "Add-Ref-Bits": 
            min_val = min(self.arb_registers[p] for p in self.frames)
            cands = [p for p in self.frames if self.arb_registers[p] == min_val]
            return min(cands, key=lambda x: self.arrival_times[x])
        return self.frames[0]

    def update_stats(self):
        total = self.hits + self.faults
        ratio = (self.hits / total * 100) if total > 0 else 0
        self.stats_lbl.config(text=f"Faults: {self.faults} | Hits: {self.hits} | Hit Ratio: {ratio:.1f}%")

    def render_frames(self, current_page, status, highlight_ptr=False, use_anim_offset=False):
        for w in self.frames_container.winfo_children(): w.destroy()
        
        req_type = ""
        if current_page is not None and self.current_step > 0:
            idx = self.current_step - 1
            if idx < len(self.requests_is_write):
                was_write = self.requests_is_write[idx]
                req_type = "(WRITE)" if was_write else "(READ)"
            
        header = f"Req: {current_page} {req_type} | {status}" if current_page is not None else "Ready"
        fg_col = "#5cb85c"
        if status and "FAULT" in status: fg_col = "#d9534f"
        
        self.info_lbl.config(text=header, fg=fg_col)

        algo = self.algo_var.get()
        if algo in ["Second-Chance", "Enhanced-Second-Chance"]:
            self.draw_clock_view(current_page, status, highlight_ptr, use_anim_offset)
        elif algo == "Add-Ref-Bits":
            self.draw_arb_table(current_page)
        else:
            self.draw_linear_view(current_page, status)

    def draw_arb_table(self, current_page):
        tk.Label(self.frames_container, text=f"Timer: {self.timer_counter}/{self.INTERRUPT_INTERVAL}", 
                 font=("Consolas", 12, "bold"), fg="#555").pack(pady=(0, 10))
        table_frame = tk.Frame(self.frames_container, bg="white")
        table_frame.pack()
        headers = ["Page ID", "Ref Bit", "History Register (8-bit)"]
        for col, text in enumerate(headers):
            tk.Label(table_frame, text=text, font=("Arial", 11, "bold"), bg="#333", fg="white", width=[15,10,25][col], relief="solid", bd=1).grid(row=0, column=col, sticky="nsew")
        
        for i, p in enumerate(self.frames):
            reg_val = self.arb_registers.get(p, 0)
            ref_val = self.ref_bits.get(p, 0)
            fg_color = "blue" if p == current_page else "black"
            tk.Label(table_frame, text=f"Page {p}", font=("Arial",11), bg="#ff7f50", fg=fg_color, relief="solid", bd=1).grid(row=i+1, column=0, sticky="nsew")
            tk.Label(table_frame, text=str(ref_val), font=("Arial",11), bg="#ffb8b8", fg=fg_color, relief="solid", bd=1).grid(row=i+1, column=1, sticky="nsew")
            tk.Label(table_frame, text=f"{reg_val:08b}", font=("Consolas",12), bg="#ffeaa7", fg=fg_color, relief="solid", bd=1).grid(row=i+1, column=2, sticky="nsew")

    def draw_linear_view(self, current_page, status):
        if self.algo_var.get() in ["FIFO", "LRU"]:
            lbl_fr = tk.Frame(self.frames_container); lbl_fr.pack()
            tk.Label(lbl_fr, text="HEAD (Old/Victim)", fg="red", font=("Arial",10,"bold")).pack(side="left", padx=50)
            tk.Label(lbl_fr, text="TAIL (New/Recent)", fg="green", font=("Arial",10,"bold")).pack(side="left", padx=50)
        box_frame = tk.Frame(self.frames_container); box_frame.pack(pady=10)
        for i in range(self.capacity):
            frame_bg, content, details = "#f9f9f9", "Empty", ""
            if i < len(self.frames):
                p = self.frames[i]
                content = f"Page {p}"
                algo = self.algo_var.get()
                if algo in ["LFU", "MFU"]: details = f"Uses: {self.freq_counter[p]}"
                elif algo == "Optimal":
                    future = self.pages[self.current_step:]
                    try: idx = future.index(p); details = f"Next: Step {self.current_step + idx + 1}"
                    except: details = "Next: NULL"
                if p == current_page: 
                    is_fault = status and "FAULT" in status
                    frame_bg = "#ffcccc" if is_fault else "#ccffcc"
            b = tk.Frame(box_frame, bg=frame_bg, bd=3, relief="ridge", width=120, height=100)
            b.grid(row=0, column=i, padx=10); b.pack_propagate(False)
            tk.Label(b, text=content, bg=frame_bg, font=("Arial", 12, "bold")).pack(pady=(25, 5))
            tk.Label(b, text=details, bg=frame_bg, font=("Consolas", 10, "bold"), fg="#333").pack()

    def draw_clock_view(self, current_page, status, highlight_ptr, use_anim_offset):
        canvas = tk.Canvas(self.frames_container, width=600, height=400, bg="white"); canvas.pack()
        cx, cy, radius = 300, 200, 120
        N = self.capacity
        if N == 0: return
        for i in range(N):
            angle = (2 * math.pi * i) / N - (math.pi / 2)
            x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            fill_color, outline_color = "#e0e0e0", "black"
            text_val, sub_text = "Empty", ""
            width = 1
            if i < len(self.frames):
                p = self.frames[i]
                text_val = f"Pg {p}"
                ref = self.ref_bits.get(p, 0); mod = self.mod_bits.get(p, 0)
                if ref == 1: fill_color = "#98fb98"; sub_text = "Ref: 1"
                else:
                    if mod == 1 and self.algo_var.get() == "Enhanced-Second-Chance": fill_color = "#ff8c00"
                    else: fill_color = "#ffd700"
                    sub_text = "Ref: 0"
                if self.algo_var.get() == "Enhanced-Second-Chance": sub_text += f"\nMod: {mod}"
                if p == current_page and not self.is_animating: outline_color = "blue"; width = 3
                if highlight_ptr and i == self.sc_pointer and not use_anim_offset: outline_color = "red"; width = 4
            canvas.create_oval(x-40, y-40, x+40, y+40, fill=fill_color, outline=outline_color, width=width)
            canvas.create_text(x, y-10, text=text_val, font=("Arial", 12, "bold"))
            canvas.create_text(x, y+15, text=sub_text, font=("Arial", 9))
        
        ptr_idx = self.sc_pointer
        if use_anim_offset: ptr_idx = self.anim_visual_start_idx + self.anim_visual_offset
        ptr_angle = (2 * math.pi * ptr_idx) / N - (math.pi / 2)
        px, py = cx + (radius - 50) * math.cos(ptr_angle), cy + (radius - 50) * math.sin(ptr_angle)
        canvas.create_line(cx, cy, px, py, width=5, fill="#333", arrow=tk.LAST, arrowshape=(16, 20, 6))
        canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#333")
        legend = "Green: Safe (Ref=1)\nGold: Best Victim (Ref=0)"
        if self.algo_var.get() == "Enhanced-Second-Chance":
            legend = "Green: Safe (Ref=1)\nGold: Best Victim (Ref=0, Mod=0)\nDk Orange: Dirty Victim (Ref=0, Mod=1)\nPriority: (0,0) > (0,1) > (1,0) > (1,1)"
        canvas.create_text(500, 350, text=legend, justify="left", font=("Arial", 10))

    def start_animated_scan(self, new_page, is_write):
        self.is_animating = True
        self.step_btn.config(state="disabled"); self.run_all_btn.config(state="disabled")
        self.esc_phase = 1; self.steps_in_phase = 0
        if self.algo_var.get() == "Enhanced-Second-Chance": self.phase_lbl.config(text="Pass 1: Looking for (0, 0)")
        else: self.phase_lbl.config(text="Scanning for Ref=0")
        self.scan_step(new_page, is_write)

    def scan_step(self, new_page, is_write):
        algo = self.algo_var.get(); p = self.frames[self.sc_pointer]
        self.render_frames(None, "SCANNING", highlight_ptr=True)
        victim_found = False; should_flip_ref = False
        if algo == "Second-Chance":
            if self.ref_bits[p] == 0: victim_found = True
            else: should_flip_ref = True
        elif algo == "Enhanced-Second-Chance":
            r = self.ref_bits[p]; m = self.mod_bits[p]
            if self.esc_phase in [1,3]: 
                if r==0 and m==0: victim_found=True
            elif self.esc_phase in [2,4]:
                if r==0 and m==1: victim_found=True
                elif r==1: should_flip_ref=True
        
        if victim_found:
            def replace():
                idx = self.frames.index(p); self.frames[idx] = new_page
                self.cleanup_metadata(p); self.init_metadata(new_page, is_write)
                self.animate_rotate_ptr(lambda: self.finish_animation(new_page, is_write, p))
            self.root.after(500, replace)
        else:
            if should_flip_ref:
                def flip():
                    self.ref_bits[p] = 0; self.render_frames(None, "SCANNING", highlight_ptr=True)
                    self.root.after(300, move_next)
                self.root.after(300, flip)
            else: self.root.after(300, lambda: move_next())
            
            def move_next():
                self.steps_in_phase += 1
                if algo == "Enhanced-Second-Chance" and self.steps_in_phase >= self.capacity:
                    self.esc_phase += 1; self.steps_in_phase = 0
                    lbl = f"Pass {self.esc_phase}"
                    self.phase_lbl.config(text=lbl)
                self.animate_rotate_ptr(lambda: self.scan_step(new_page, is_write))

    def animate_rotate_ptr(self, on_complete):
        start = self.sc_pointer; self.sc_pointer = (self.sc_pointer + 1) % self.capacity
        steps = 5; delay = 20
        def anim(s):
            self.anim_visual_offset = s/steps; self.anim_visual_start_idx = start
            self.render_frames(None, "SCANNING", use_anim_offset=True)
            if s<steps: self.root.after(delay, lambda: anim(s+1))
            else: self.anim_visual_offset=0; on_complete()
        anim(1)

    def finish_animation(self, page, is_write, victim):
        self.is_animating = False
        self.step_btn.config(state="normal"); self.run_all_btn.config(state="normal")
        self.finalize_step_ui(page, "FAULT", is_write, victim)

    def calc_frag(self):
        try:
            self.frag_canvas.delete("all")
            proc_s = float(self.frag_proc_size.get()); page_s = float(self.frag_page_size.get())
            if page_s <= 0 or proc_s <= 0: raise ValueError
            num_pages = math.ceil(proc_s / page_s); total = num_pages * page_s; frag = total - proc_s
            cx, cy, r = 250, 200, 120; used_ang = (proc_s / total) * 360
            self.frag_canvas.create_text(cx, 40, text="Total Memory Efficiency", font=("Arial", 14, "bold"))
            self.frag_canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=used_ang, fill="#66bb6a", outline="white")
            self.frag_canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=90+used_ang, extent=360-used_ang, fill="#ef5350", outline="white")
            self.frag_canvas.create_text(cx, cy+r+30, text=f"Total Frag: {frag:.2f} KB")
            cx2 = 750; self.frag_canvas.create_text(cx2, 40, text="Last Page Fragmentation", font=("Arial", 14, "bold"))
            used_last = page_s - frag; last_used_ang = (used_last / page_s) * 360; last_frag_ang = 360 - last_used_ang
            self.frag_canvas.create_arc(cx2-r, cy-r, cx2+r, cy+r, start=90, extent=last_used_ang, fill="#66bb6a", outline="white")
            self.frag_canvas.create_arc(cx2-r, cy-r, cx2+r, cy+r, start=90+last_used_ang, extent=last_frag_ang, fill="#ef5350", outline="white")
            self.frag_canvas.create_text(cx2, cy+r+30, text=f"Last Page: {used_last:.2f} KB Used / {frag:.2f} KB Wasted")
            self.frag_result_text.set(f"Pages: {num_pages} | Total: {total}KB | Frag: {frag:.2f}KB ({(frag/total)*100:.1f}%)")
            self.frag_canvas.create_text(400, 100, text="Green: Used\nRed: Wasted", font=("Arial", 12))
        except ValueError: messagebox.showerror("Error", "Invalid numbers")

if __name__ == "__main__":
    root = tk.Tk()
    app = VirtualMemorySimulator(root)
    root.mainloop()
