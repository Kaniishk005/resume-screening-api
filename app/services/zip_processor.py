import os
import zipfile
from pathlib import Path


def extract_zip(zip_path: str, output_folder: str):

    os.makedirs(output_folder, exist_ok=True)

    output_root = Path(output_folder).resolve()
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            target = (output_root / member.filename).resolve()
            if output_root not in target.parents and target != output_root:
                raise ValueError("ZIP archive contains an unsafe path.")
            if member.is_dir():
                continue
            if target.suffix.lower() != ".pdf":
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zip_ref.open(member) as source, open(target, "wb") as destination:
                destination.write(source.read())

    pdf_files = []

    for root, _, files in os.walk(output_folder):

        for file in files:

            if file.lower().endswith(".pdf"):

                pdf_files.append(
                    os.path.join(root, file)
                )

    return pdf_files
