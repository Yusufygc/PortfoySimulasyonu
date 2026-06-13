import json
from pathlib import Path

from scripts import measure_code_quality


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_measure_file_excludes_comments_blank_lines_and_docstrings(tmp_path):
    path = _write(
        tmp_path / "src" / "sample.py",
        '''"""module docstring"""
# standalone comment
VALUE = 1  # inline comment


class Sample:
    """class docstring"""

    def method(self, first, second):
        """method docstring"""
        if first and second:
            return first
        return second
''',
    )

    result = measure_code_quality.measure_file(path, tmp_path)
    file_record = result["file"]
    method_record = next(record for record in result["functions"] if record["name"] == "method")

    assert file_record["comment_lines"] == 1
    assert file_record["inline_comment_lines"] == 1
    assert file_record["blank_lines"] == 3
    assert file_record["docstring_lines"] == 3
    assert file_record["effective_code_lines"] < file_record["code_lines"]
    assert method_record["effective_param_count"] == 2
    assert method_record["raw_param_count"] == 3


def test_threshold_violations_are_reported_for_classes_and_functions(tmp_path):
    methods = "\n".join(f"    def method_{index}(self):\n        return {index}" for index in range(21))
    path = _write(
        tmp_path / "src" / "ui" / "pages" / "large_page.py",
        f"""class LargePage:
{methods}

def too_many_params(a, b, c, d, e, f):
    return a
""",
    )

    result = measure_code_quality.measure_file(path, tmp_path)
    class_record = result["classes"][0]
    function_record = next(record for record in result["functions"] if record["name"] == "too_many_params")

    assert class_record["threshold_status"] == "violation"
    assert "class_methods" in class_record["violations"]
    assert function_record["threshold_status"] == "violation"
    assert "function_effective_params" in function_record["violations"]


def test_report_outputs_are_sorted_and_written_with_fixed_baseline_date(tmp_path):
    _write(tmp_path / "src" / "b.py", "B = 1\n")
    _write(tmp_path / "src" / "a.py", "A = 1\n")
    output_dir = tmp_path / "docs" / "wiki"

    report = measure_code_quality.build_report(tmp_path, tmp_path / "missing.html")
    md_path, json_path = measure_code_quality.write_outputs(report, output_dir)

    assert [record["path"] for record in report["files"]] == ["src/a.py", "src/b.py"]
    assert report["metadata"]["baseline_date"] == "2026-06-13"
    assert md_path.name == "code_quality_baseline_2026-06-13.md"
    assert json_path.name == "code_quality_baseline_2026-06-13.json"
    assert json.loads(json_path.read_text(encoding="utf-8"))["metadata"]["generated_at"] == "2026-06-13"


def test_health_report_crosswalk_matches_basename_only_paths(tmp_path):
    _write(tmp_path / "src" / "application" / "service.py", "VALUE = 1\n")
    report = _write(
        tmp_path / "PortfoySimulasyonu_saglik_raporu.html",
        '<span class="path">service.py</span>',
    )

    paths = measure_code_quality.health_report_paths(report, tmp_path)

    assert paths == ["src/application/service.py"]


def test_repo_measurement_smoke():
    report = measure_code_quality.build_report(measure_code_quality.ROOT)

    assert report["summary"]["file_count"] > 0
    assert report["summary"]["effective_code_lines"] > 0
    assert {"src", "tests", "scripts", "root"} <= set(report["summary"]["by_layer"])
