from explorer.utils import get_file_content


def test_get_file_content(tmp_path):
    file = tmp_path / "sample.txt"
    file.write_text("hello")
    assert get_file_content(str(file)) == "hello"
