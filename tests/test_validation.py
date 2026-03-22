from __future__ import annotations

import pytest

from bitbucket_mcp.validation import (
    ValidationError,
    clamp_context_lines,
    clamp_limit,
    clamp_start,
    validate_base_url,
    validate_branch_name,
    validate_commit_id,
    validate_path,
    validate_positive_int,
    validate_project_key,
    validate_repo_slug,
    validate_tag_name,
)


class TestValidateBaseUrl:
    def test_valid_https(self):
        assert (
            validate_base_url("https://bitbucket.example.com")
            == "https://bitbucket.example.com"
        )

    def test_strips_trailing_slash(self):
        assert (
            validate_base_url("https://bitbucket.example.com/")
            == "https://bitbucket.example.com"
        )

    def test_http_rejected(self):
        with pytest.raises(ValidationError, match="https://"):
            validate_base_url("http://localhost:7990")

    def test_invalid_scheme(self):
        with pytest.raises(ValidationError, match="https://"):
            validate_base_url("ftp://bitbucket.example.com")

    def test_no_host(self):
        with pytest.raises(ValidationError, match="host"):
            validate_base_url("https://")


class TestValidateProjectKey:
    def test_valid_keys(self):
        assert validate_project_key("PROJ") == "PROJ"
        assert validate_project_key("MY_PROJECT_123") == "MY_PROJECT_123"
        assert validate_project_key("~username") == "~username"

    def test_invalid_keys(self):
        with pytest.raises(ValidationError):
            validate_project_key("PROJ/repos")
        with pytest.raises(ValidationError):
            validate_project_key("../admin")
        with pytest.raises(ValidationError):
            validate_project_key("")
        with pytest.raises(ValidationError):
            validate_project_key("has space")


class TestValidateRepoSlug:
    def test_valid_slugs(self):
        assert validate_repo_slug("my-repo") == "my-repo"
        assert validate_repo_slug("repo123") == "repo123"
        assert validate_repo_slug("my.repo") == "my.repo"

    def test_invalid_slugs(self):
        with pytest.raises(ValidationError):
            validate_repo_slug("-starts-with-hyphen")
        with pytest.raises(ValidationError):
            validate_repo_slug("has/slash")
        with pytest.raises(ValidationError):
            validate_repo_slug("../traversal")
        with pytest.raises(ValidationError):
            validate_repo_slug("")


class TestValidatePath:
    def test_valid_paths(self):
        assert validate_path("") == ""
        assert validate_path("src/main.py") == "src/main.py"
        assert validate_path("README.md") == "README.md"
        assert validate_path("src/com.example/App.java") == "src/com.example/App.java"

    def test_traversal_blocked(self):
        with pytest.raises(ValidationError, match="traversal"):
            validate_path("../../admin")
        with pytest.raises(ValidationError, match="traversal"):
            validate_path("src/../../etc/passwd")

    def test_leading_slash_blocked(self):
        with pytest.raises(ValidationError, match="must not start"):
            validate_path("/etc/passwd")

    def test_null_byte_blocked(self):
        with pytest.raises(ValidationError, match="null"):
            validate_path("file\x00.txt")


class TestValidateCommitId:
    def test_valid(self):
        assert validate_commit_id("abc123") == "abc123"
        assert (
            validate_commit_id("abc123def456789012345678901234567890abcd")
            == "abc123def456789012345678901234567890abcd"
        )

    def test_invalid(self):
        with pytest.raises(ValidationError):
            validate_commit_id("not-a-sha")
        with pytest.raises(ValidationError):
            validate_commit_id("ab")  # too short
        with pytest.raises(ValidationError):
            validate_commit_id("../admin")


class TestValidatePositiveInt:
    def test_valid(self):
        assert validate_positive_int(1, "id") == 1
        assert validate_positive_int(999, "id") == 999

    def test_invalid(self):
        with pytest.raises(ValidationError):
            validate_positive_int(0, "id")
        with pytest.raises(ValidationError):
            validate_positive_int(-1, "id")


class TestClampFunctions:
    def test_clamp_limit(self):
        assert clamp_limit(25) == 25
        assert clamp_limit(0) == 1
        assert clamp_limit(-5) == 1
        assert clamp_limit(5000) == 1000

    def test_clamp_start(self):
        assert clamp_start(0) == 0
        assert clamp_start(10) == 10
        assert clamp_start(-1) == 0

    def test_clamp_context_lines(self):
        assert clamp_context_lines(10) == 10
        assert clamp_context_lines(-5) == 0
        assert clamp_context_lines(999) == 100


class TestValidateBranchName:
    def test_valid_names(self):
        assert validate_branch_name("main") == "main"
        assert validate_branch_name("feature/my-branch") == "feature/my-branch"
        assert validate_branch_name("release/v1.0.0") == "release/v1.0.0"
        assert validate_branch_name("fix_bug-123") == "fix_bug-123"

    def test_invalid_names(self):
        with pytest.raises(ValidationError):
            validate_branch_name("")
        with pytest.raises(ValidationError):
            validate_branch_name("../escape")
        with pytest.raises(ValidationError):
            validate_branch_name("foo/../bar")
        with pytest.raises(ValidationError):
            validate_branch_name("/leading-slash")
        with pytest.raises(ValidationError):
            validate_branch_name("-starts-with-hyphen")

    def test_rejects_double_slashes(self):
        with pytest.raises(ValidationError):
            validate_branch_name("feature//x")

    def test_rejects_trailing_slash(self):
        with pytest.raises(ValidationError):
            validate_branch_name("feature/")


class TestValidateTagName:
    def test_valid_names(self):
        assert validate_tag_name("v1.0.0") == "v1.0.0"
        assert validate_tag_name("release/2024/q1") == "release/2024/q1"
        assert validate_tag_name("v1.0.0-rc.1") == "v1.0.0-rc.1"

    def test_invalid_names(self):
        with pytest.raises(ValidationError):
            validate_tag_name("")
        with pytest.raises(ValidationError):
            validate_tag_name("../escape")
        with pytest.raises(ValidationError):
            validate_tag_name("foo/../bar")

    def test_rejects_double_slashes(self):
        with pytest.raises(ValidationError):
            validate_tag_name("release//v1")

    def test_rejects_trailing_slash(self):
        with pytest.raises(ValidationError):
            validate_tag_name("release/")
