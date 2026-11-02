"""The copies listed in PROJECT_MAP.md stay identical to the canonical files."""

import hashlib
import unittest

from common import APP_ROOT
from src.config import DATA, DATASETS, MODELS

PROJECT = APP_ROOT.parent
DATA_COPIES = [PROJECT / "AI Trim & Fuse/Dataset/trimfuse_synthetic_dataset/trimfuse_synth/data", PROJECT / "Colab Notebook"]
MODEL_FILES = ["trim_models.joblib", "pmic_models.joblib", "sensor_models.joblib", "soc_models.joblib", "evaluation_06.json"]


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


class Copies(unittest.TestCase):
    def test_dataset_copies_match_canonical(self):
        for f, *_ in DATASETS.values():
            for d in DATA_COPIES:
                if (d / f).exists():
                    with self.subTest(f"{d.name}/{f}"):
                        self.assertEqual(md5(d / f), md5(DATA / f))

    def test_notebook_models_match_app_models(self):
        for f in MODEL_FILES:
            nb = PROJECT / "Colab Notebook" / f
            if nb.exists():  # regenerable, so it may be absent in the submission zip
                with self.subTest(f):
                    self.assertEqual(md5(nb), md5(MODELS / f))

    def test_repo_root_deploy_files_match_the_app(self):
        """Streamlit Community Cloud reads requirements.txt and .streamlit/config.toml from the repo root."""
        app_req = (APP_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        root_req = (PROJECT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual([x for x in root_req if not x.startswith("# Copy of") and "keeps the two files" not in x], app_req)
        self.assertEqual(md5(PROJECT / ".streamlit/config.toml"), md5(APP_ROOT / ".streamlit/config.toml"))

    def test_canonical_files_exist(self):
        for p in [*(DATA / f for f, *_ in DATASETS.values()), *(MODELS / f for f in MODEL_FILES),
                  PROJECT / "RESULTS_SOURCE_OF_TRUTH.csv", PROJECT / "Demo/expected_results.csv"]:
            with self.subTest(p.name):
                self.assertTrue(p.exists())


if __name__ == "__main__":
    unittest.main()
