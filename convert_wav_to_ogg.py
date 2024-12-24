import os
from tkinter import Tk, filedialog
from pydub import AudioSegment

def convert_audio_to_ogg():
    # Hide the Tkinter root window
    root = Tk()
    root.withdraw()

    # Ask the user to select files (.wav, .aiff, .mp3)
    file_paths = filedialog.askopenfilenames(
        title="Select Audio Files",
        filetypes=[("Audio files", "*.wav *.aiff *.mp3")]
    )

    if not file_paths:
        print("No files selected. Exiting.")
        return

    # Ask the user for an output directory
    output_dir = filedialog.askdirectory(
        title="Select Output Directory"
    )

    if not output_dir:
        print("No output directory selected. Exiting.")
        return

    # Supported formats
    supported_formats = [".wav", ".aiff", ".mp3"]

    for input_path in file_paths:
        file_name = os.path.basename(input_path)
        file_extension = os.path.splitext(file_name)[1].lower()

        if file_extension not in supported_formats:
            print(f"Skipping unsupported file: {file_name}")
            continue

        output_path = os.path.join(output_dir, file_name.replace(file_extension, ".ogg"))

        # Load the audio file based on its format
        audio = AudioSegment.from_file(input_path, format=file_extension[1:])  # Removes the dot (e.g., "wav", "aiff", "mp3")

        # Export as .ogg
        audio.export(output_path, format="ogg")
        print(f"Converted: {file_name} -> {output_path}")

# Run the function
if __name__ == "__main__":
    convert_audio_to_ogg()
