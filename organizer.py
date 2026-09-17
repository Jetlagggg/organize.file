import os
import shutil
import sys
from pathlib import Path

# Folder yang TIDAK BOLEH dirapikan sama sekali (proteksi).
# Ini folder-folder sistem penting — kalau ke-organize bisa bikin masalah besar.
PROTECTED_FOLDERS = {
    "/", "/root", "/home", "/etc", "/usr", "/bin", "/sbin", "/lib",
    "/System", "/Library", "/Applications", "/Windows",
    "C:\\", "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
}

# Mapping ekstensi -> nama folder tujuan
FILE_CATEGORIES = {
    "Gambar": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"],
    "Dokumen": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv"],
    "Video": [".mp4", ".mkv", ".mov", ".avi"],
    "Musik": [".mp3", ".wav", ".flac"],
    "Arsip": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Kode": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c"],
    "Installer": [".exe", ".msi", ".apk", ".deb"],
}

# Pengelompokan tambahan berdasarkan kata kunci di nama file, per kategori.
# Kalau nama file mengandung salah satu keyword ini (case-insensitive),
# file akan dimasukkan ke subfolder tambahan di dalam kategori tersebut.
# Contoh: "Laporan_Bulanan.docx" di kategori "Dokumen" -> Dokumen/Laporan/
#
# Silakan tambah/ubah sesuai kebutuhan.
KEYWORD_SUBGROUPS = {
    "Dokumen": {
        "laporan": "Laporan",
        "invoice": "Invoice",
        "tugas": "Tugas",
    },
    # "Gambar": {
    #     "screenshot": "Screenshot",
    # },
}


def get_common_folders():
    """Kembalikan daftar folder umum (Downloads, Documents, Desktop, Pictures)
    yang ada di komputer user, kalau memang ada."""
    home = Path.home()
    candidates = {
        "Downloads": home / "Downloads",
        "Documents": home / "Documents",
        "Desktop": home / "Desktop",
        "Pictures": home / "Pictures",
    }
    return {name: str(path) for name, path in candidates.items() if path.is_dir()}


def is_protected(folder_path):
    """Cek apakah folder ini termasuk folder sistem yang dilindungi,
    atau folder root/home itu sendiri (biar gak ke-scan semua isi laptop)."""
    resolved = str(Path(folder_path).resolve())
    home_resolved = str(Path.home().resolve())

    if resolved in PROTECTED_FOLDERS:
        return True
    if resolved == home_resolved:
        return True
    # Cek juga versi tanpa trailing slash utk perbandingan drive root Windows
    if len(resolved) <= 3 and resolved.endswith(":\\"):
        return True
    return False


def choose_folder_interactively():
    """Tanya user mau organize folder yang mana."""
    common = get_common_folders()

    print("Folder mana yang mau dirapikan?\n")
    options = list(common.items())
    for i, (name, path) in enumerate(options, start=1):
        print(f"  {i}. {name}  ({path})")
    print(f"  {len(options) + 1}. Masukkan path folder lain secara manual")

    choice = input("\nPilih nomor: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1][1]
    else:
        manual_path = input("Masukkan path lengkap folder: ").strip().strip('"')
        return manual_path


def get_category(filename):
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Lainnya"


def get_subgroup(filename, category):
    """Cek apakah nama file cocok dengan salah satu keyword subgroup
    di kategori ini. Return nama subfolder atau None kalau tidak cocok."""
    rules = KEYWORD_SUBGROUPS.get(category, {})
    name_lower = filename.lower()
    for keyword, subfolder in rules.items():
        if keyword.lower() in name_lower:
            return subfolder
    return None


def organize_folder(folder_path, dry_run=False):
    if not os.path.isdir(folder_path):
        print(f"Folder tidak ditemukan: {folder_path}")
        return

    if is_protected(folder_path):
        print(f"DIBATALKAN: '{folder_path}' adalah folder sistem/home yang dilindungi.")
        print("Script ini tidak akan menjalankan organize di folder tersebut demi keamanan.")
        return

    moved_count = 0
    skipped_count = 0
    error_count = 0

    for filename in os.listdir(folder_path):
        source_path = os.path.join(folder_path, filename)

        # Skip folder (termasuk folder hasil organize sebelumnya)
        if os.path.isdir(source_path):
            continue

        # Skip file tersembunyi/system (misal .DS_Store, .gitignore, desktop.ini)
        if filename.startswith(".") or filename.lower() in ("desktop.ini", "thumbs.db"):
            skipped_count += 1
            continue

        # Jangan pindahin script ini sendiri kalau kebetulan ada di folder yang sama
        if os.path.abspath(source_path) == os.path.abspath(__file__):
            skipped_count += 1
            continue

        category = get_category(filename)
        subgroup = get_subgroup(filename, category)

        if subgroup:
            dest_folder = os.path.join(folder_path, category, subgroup)
        else:
            dest_folder = os.path.join(folder_path, category)

        dest_path = os.path.join(dest_folder, filename)

        # Hindari overwrite kalau nama file udah ada di tujuan
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            dest_path = os.path.join(dest_folder, f"{base}_copy{ext}")

        shown_path = f"{category}/{subgroup}/" if subgroup else f"{category}/"

        if dry_run:
            print(f"[DRY RUN] Akan dipindah: {filename} -> {shown_path}")
            moved_count += 1
            continue

        try:
            os.makedirs(dest_folder, exist_ok=True)
            shutil.move(source_path, dest_path)
            print(f"Dipindah: {filename} -> {shown_path}")
            moved_count += 1
        except (PermissionError, OSError) as e:
            print(f"GAGAL memindah '{filename}': {e}")
            error_count += 1

    print(f"\nSelesai! {moved_count} file dirapikan, {skipped_count} dilewati, {error_count} gagal.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_folder = sys.argv[1]
    else:
        target_folder = choose_folder_interactively()

    if not target_folder:
        print("Tidak ada folder yang dipilih. Keluar.")
        sys.exit(0)

    if is_protected(target_folder):
        print(f"\nDIBATALKAN: '{target_folder}' adalah folder sistem/home yang dilindungi.")
        sys.exit(1)

    confirm = input(
        f"\nFolder yang akan dirapikan: {target_folder}\n"
        f"Lanjutkan? Ini akan MEMINDAHKAN file (bukan copy). (y/n): "
    ).strip().lower()

    if confirm != "y":
        print("Dibatalkan.")
        sys.exit(0)

    organize_folder(target_folder)