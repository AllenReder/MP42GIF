import os
import cv2
import yaml
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import StringVar, IntVar
import tkinter.scrolledtext as st

# ===== 读取多语言文件 =====
def load_language(lang_code):
    lang_file = os.path.join("lang", f"{lang_code}.yaml")
    if not os.path.exists(lang_file):
        raise FileNotFoundError(f"Language file not found: {lang_file}")
    with open(lang_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ==== Video processing function ====
def mp4_to_png_sequence(mp4_path, output_dir, target_width, target_height, num_frames,
                        logger=None, t_func=lambda k: k, progress_callback=None):
    if logger is None:
        logger = print

    cap = cv2.VideoCapture(mp4_path)
    if not cap.isOpened():
        raise IOError(t_func("cannot_open_video").format(path=mp4_path))

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_sec = (total_frames / fps) if fps > 0 else 0.0

    logger(f"{t_func('video_info')}:")
    logger(f"  {t_func('orig_size_label')}: {width}x{height}")
    logger(f"  {t_func('total_frames_label')}: {total_frames}")
    logger(f"  {t_func('fps_label')}: {fps:.2f}")
    logger(f"  {t_func('duration_label')}: {duration_sec:.2f} {t_func('seconds')}")

    if total_frames <= 0:
        cap.release()
        raise IOError("Video has no frames or cannot read frame count.")

    frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    logger(t_func("cleared_output_dir").format(dir=output_dir))

    for i, frame_idx in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            logger(t_func("warning_frame_read_failed").format(idx=frame_idx))
            if progress_callback:
                progress_callback(i + 1, len(frame_indices))
            continue

        try:
            resized_frame = cv2.resize(frame, (target_width, target_height))
        except Exception:
            logger(t_func("warning_frame_read_failed").format(idx=frame_idx))
            if progress_callback:
                progress_callback(i + 1, len(frame_indices))
            continue

        output_path = os.path.join(output_dir, f"frame_{i+1:04d}.png")
        cv2.imwrite(output_path, resized_frame)
        logger(t_func("saved_file").format(path=output_path))

        if progress_callback:
            progress_callback(i + 1, len(frame_indices))

    cap.release()
    logger(t_func("conversion_complete"))

# ==== GUI ====
class MP4ToPNGConverter:
    def __init__(self):
        self.language = "zh"
        self.translations = load_language(self.language)

        self.root = tk.Tk()
        self.root.title(self.t("title"))
        self.root.geometry("640x520")
        self.root.resizable(False, False)

        self.mp4_path = StringVar()
        self.output_dir = StringVar(value="output")
        self.target_width = IntVar()
        self.target_height = IntVar()
        self.num_frames = IntVar(value=50)

        self.video_info = {
            'width': 0,
            'height': 0,
            'fps': 0,
            'total_frames': 0,
            'duration': 0
        }

        self._widgets = {}
        self.create_widgets()

    def t(self, key):
        return self.translations.get(key, key)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        lbl_lang = ttk.Label(main_frame, text=self.t("lang_label"))
        lbl_lang.grid(row=0, column=0, sticky=tk.W, pady=5)
        self._widgets['lbl_lang'] = lbl_lang

        self.lang_box = ttk.Combobox(main_frame, values=["中文", "English"], width=12, state="readonly")
        self.lang_box.current(0)
        self.lang_box.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.lang_box.bind("<<ComboboxSelected>>", self.change_language)

        lbl_mp4 = ttk.Label(main_frame, text=self.t("select_mp4"))
        lbl_mp4.grid(row=1, column=0, sticky=tk.W, pady=5)
        self._widgets['lbl_mp4'] = lbl_mp4

        entry_mp4 = ttk.Entry(main_frame, textvariable=self.mp4_path, width=50)
        entry_mp4.grid(row=1, column=1, padx=5, pady=5)

        btn_browse_file = ttk.Button(main_frame, text=self.t("browse"), command=self.select_file)
        btn_browse_file.grid(row=1, column=2, padx=5, pady=5)
        self._widgets['btn_browse_file'] = btn_browse_file

        lbl_output = ttk.Label(main_frame, text=self.t("output_dir"))
        lbl_output.grid(row=2, column=0, sticky=tk.W, pady=5)
        self._widgets['lbl_output'] = lbl_output

        entry_output = ttk.Entry(main_frame, textvariable=self.output_dir, width=50)
        entry_output.grid(row=2, column=1, padx=5, pady=5)

        btn_browse_out = ttk.Button(main_frame, text=self.t("browse"), command=self.select_output_dir)
        btn_browse_out.grid(row=2, column=2, padx=5, pady=5)
        self._widgets['btn_browse_out'] = btn_browse_out

        lbl_size = ttk.Label(main_frame, text=self.t("png_size"))
        lbl_size.grid(row=3, column=0, sticky=tk.W, pady=5)
        self._widgets['lbl_size'] = lbl_size

        size_frame = ttk.Frame(main_frame)
        size_frame.grid(row=3, column=1, sticky=tk.W, pady=5)

        lbl_w = ttk.Label(size_frame, text=self.t("width"))
        lbl_w.grid(row=0, column=0)
        self._widgets['lbl_w'] = lbl_w

        entry_w = ttk.Entry(size_frame, textvariable=self.target_width, width=12)
        entry_w.grid(row=0, column=1, padx=5)

        lbl_h = ttk.Label(size_frame, text=self.t("height"))
        lbl_h.grid(row=0, column=2, padx=10)
        self._widgets['lbl_h'] = lbl_h

        entry_h = ttk.Entry(size_frame, textvariable=self.target_height, width=12)
        entry_h.grid(row=0, column=3, padx=5)

        lbl_count = ttk.Label(main_frame, text=self.t("png_count"))
        lbl_count.grid(row=4, column=0, sticky=tk.W, pady=5)
        self._widgets['lbl_count'] = lbl_count

        entry_count = ttk.Entry(main_frame, textvariable=self.num_frames, width=12)
        entry_count.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)

        info_label = ttk.Label(main_frame, text=self.t("video_info"))
        info_label.grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
        self._widgets['info_label'] = info_label

        self.info_text = tk.Text(main_frame, height=5, width=76, state=tk.DISABLED)
        self.info_text.grid(row=6, column=0, columnspan=3, pady=5)

        log_label = ttk.Label(main_frame, text="Log:")
        log_label.grid(row=7, column=0, sticky=tk.W, pady=(10, 0))
        self._widgets['log_label'] = log_label

        self.log_box = st.ScrolledText(main_frame, height=10, width=76, state=tk.DISABLED)
        self.log_box.grid(row=8, column=0, columnspan=3, pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=3, pady=10)

        btn_start = ttk.Button(button_frame, text=self.t("start"), command=self.start_conversion)
        btn_start.pack(side=tk.LEFT, padx=5)
        self._widgets['btn_start'] = btn_start

        btn_exit = ttk.Button(button_frame, text=self.t("exit"), command=self.root.quit)
        btn_exit.pack(side=tk.LEFT, padx=5)
        self._widgets['btn_exit'] = btn_exit

    def change_language(self, event=None):
        selected = self.lang_box.get()
        self.language = "zh" if selected == "中文" else "en"
        self.translations = load_language(self.language)
        self.update_labels()

    def update_labels(self):
        self.root.title(self.t("title"))
        self._widgets['lbl_lang'].config(text=self.t("lang_label"))
        self._widgets['lbl_mp4'].config(text=self.t("select_mp4"))
        self._widgets['btn_browse_file'].config(text=self.t("browse"))
        self._widgets['lbl_output'].config(text=self.t("output_dir"))
        self._widgets['btn_browse_out'].config(text=self.t("browse"))
        self._widgets['lbl_size'].config(text=self.t("png_size"))
        self._widgets['lbl_w'].config(text=self.t("width"))
        self._widgets['lbl_h'].config(text=self.t("height"))
        self._widgets['lbl_count'].config(text=self.t("png_count"))
        self._widgets['btn_start'].config(text=self.t("start"))
        self._widgets['btn_exit'].config(text=self.t("exit"))
        self._widgets['info_label'].config(text=self.t("video_info"))
        self.lang_box.set("中文" if self.language == "zh" else "English")
        self.update_info_display()

    def log(self, message):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, str(message) + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title=self.t("select_mp4"),
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if file_path:
            self.mp4_path.set(file_path)
            self.load_video_info()

    def select_output_dir(self):
        dir_path = filedialog.askdirectory(title=self.t("output_dir"))
        if dir_path:
            self.output_dir.set(dir_path)

    def load_video_info(self):
        try:
            cap = cv2.VideoCapture(self.mp4_path.get())
            if not cap.isOpened():
                messagebox.showerror(self.t("error"), self.t("cannot_open_video").format(path=self.mp4_path.get()))
                return

            self.video_info['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            self.video_info['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            self.video_info['fps'] = cap.get(cv2.CAP_PROP_FPS) or 0.0
            self.video_info['total_frames'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            self.video_info['duration'] = (
                self.video_info['total_frames'] / self.video_info['fps']
            ) if self.video_info['fps'] > 0 else 0.0
            cap.release()

            self.target_width.set(self.video_info['width'])
            self.target_height.set(self.video_info['height'])

            self.update_info_display()
        except Exception as e:
            messagebox.showerror(self.t("error"), str(e))

    def update_info_display(self):
        info = (
            f"{self.t('video_info')}:\n"
            f"  {self.t('orig_size_label')}: {self.video_info['width']}x{self.video_info['height']}\n"
            f"  {self.t('total_frames_label')}: {self.video_info['total_frames']}\n"
            f"  {self.t('fps_label')}: {self.video_info['fps']:.2f}\n"
            f"  {self.t('duration_label')}: {self.video_info['duration']:.2f} {self.t('seconds')}"
        )
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info)
        self.info_text.config(state=tk.DISABLED)

    def start_conversion(self):
        if not self.mp4_path.get():
            messagebox.showerror(self.t("error"), self.t("select_mp4_first"))
            return
        if not self.output_dir.get():
            messagebox.showerror(self.t("error"), self.t("select_output_first"))
            return
        try:
            width = int(self.target_width.get())
            height = int(self.target_height.get())
            num_frames = int(self.num_frames.get())
            if width <= 0 or height <= 0:
                messagebox.showerror(self.t("error"), self.t("size_must_gt_0"))
                return
            if num_frames <= 0:
                messagebox.showerror(self.t("error"), self.t("count_must_gt_0"))
                return

            self.log_box.config(state=tk.NORMAL)
            self.log_box.delete(1.0, tk.END)
            self.log_box.config(state=tk.DISABLED)

            self.root.config(cursor="watch")
            self.root.update_idletasks()

            mp4_to_png_sequence(
                self.mp4_path.get(),
                self.output_dir.get(),
                width,
                height,
                num_frames,
                logger=self.log,
                t_func=self.t,
                progress_callback=lambda i, n: self.root.update_idletasks()
            )

            self.root.config(cursor="")
            messagebox.showinfo(self.t("done"), self.t("conversion_done"))
        except Exception as e:
            self.root.config(cursor="")
            messagebox.showerror(self.t("error"), str(e))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MP4ToPNGConverter()
    app.run()
