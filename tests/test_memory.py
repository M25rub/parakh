import os

os.environ.setdefault("PARAKH_MOCK", "1")

from unittest.mock import MagicMock, patch  # noqa: E402

from parakh import memory  # noqa: E402


def _use_temp_file(monkeypatch, tmp_path):
    monkeypatch.setattr(memory, "LOCAL_FILE", tmp_path / "memory.json")
    monkeypatch.setenv("MEMORY_BACKEND", "local")


def test_save_then_lookup(monkeypatch, tmp_path):
    _use_temp_file(monkeypatch, tmp_path)
    memory.save(["hec-gov-pk.com"], "likely_scam", "Fake HEC fee request")
    rec = memory.lookup(["other.com", "HEC-GOV-PK.com"])
    assert rec["report_count"] == 1 and rec["risk"] == "likely_scam"


def test_report_count_increments(monkeypatch, tmp_path):
    _use_temp_file(monkeypatch, tmp_path)
    memory.save(["scam.example"], "suspicious", "x")
    memory.save(["scam.example"], "likely_scam", "y")
    assert memory.lookup(["scam.example"])["report_count"] == 2


def test_verified_is_never_saved(monkeypatch, tmp_path):
    _use_temp_file(monkeypatch, tmp_path)
    memory.save(["hec.gov.pk"], "verified", "real")
    assert memory.lookup(["hec.gov.pk"]) is None


def test_unknown_returns_none(monkeypatch, tmp_path):
    _use_temp_file(monkeypatch, tmp_path)
    assert memory.lookup(["nobody.com"]) is None
    assert memory.lookup([]) is None


def test_broken_file_does_not_crash(monkeypatch, tmp_path):
    _use_temp_file(monkeypatch, tmp_path)
    (tmp_path / "memory.json").write_text("{not json")
    assert memory.lookup(["x.com"]) is None


def test_firestore_failure_falls_back_to_local(monkeypatch, tmp_path):
    _use_temp_file(monkeypatch, tmp_path)
    monkeypatch.setenv("MEMORY_BACKEND", "firestore")
    with patch.object(memory, "_firestore_client", side_effect=Exception("no credentials")):
        memory.save(["fallback.example"], "likely_scam", "z")
        assert memory.lookup(["fallback.example"])["report_count"] == 1


def test_firestore_lookup_with_fake_client(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "firestore")
    snap = MagicMock(exists=True)
    snap.to_dict.return_value = {"indicator": "bad.com", "report_count": 3}
    client = MagicMock()
    client.collection.return_value.document.return_value.get.return_value = snap
    with patch.object(memory, "_firestore_client", return_value=client):
        assert memory.lookup(["bad.com"])["report_count"] == 3
        

def test_firestore_client_reads_secret_json(monkeypatch):
    monkeypatch.setattr(memory, "_client", None)
    monkeypatch.setenv("FIRESTORE_CREDENTIALS_JSON", '{"project_id": "demo-proj"}')
    fake_creds = MagicMock()
    with patch("google.oauth2.service_account.Credentials.from_service_account_info",
               return_value=fake_creds) as make_creds, \
         patch("google.cloud.firestore.Client") as client_cls:
        memory._firestore_client()
    make_creds.assert_called_once()
    client_cls.assert_called_once_with(project="demo-proj", credentials=fake_creds)
    monkeypatch.setattr(memory, "_client", None)  # don't leak the fake client