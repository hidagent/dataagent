"""Rule file parser for Agent Rules.

This module handles parsing of rule files in Markdown format with YAML frontmatter.
It supports:
- YAML frontmatter parsing for metadata
- Required field validation (name, description)
- File size limits for security
- File reference resolution (#[[file:path]])
- Path safety validation to prevent directory traversal
"""

import logging
import re
from pathlib import Path
from typing import Any

from dataagent_core.rules.models import Rule, RuleScope, RuleInclusion


logger = logging.getLogger(__name__)

# Maximum rule file size (1MB)
MAX_RULE_FILE_SIZE = 1 * 1024 * 1024


class RuleParseError(Exception):
    """Exception raised when rule parsing fails."""
    pass


class RuleParser:
    """Parser for rule files.
    
    Parses Markdown files with YAML frontmatter into Rule objects.
    
    Example rule file format:
    ```markdown
    ---
    name: coding-standards
    description: Python coding standards
    inclusion: always
    priority: 60
    ---
    
    # Coding Standards
    
    Follow PEP 8 guidelines...
    ```
    """

    # Pattern to match YAML frontmatter between --- delimiters
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
    
    # Pattern to match file references: #[[file:path/to/file]]
    FILE_REFERENCE_PATTERN = re.compile(r"#\[\[file:([^\]]+)\]\]")

    def parse_file(self, file_path: Path, scope: RuleScope) -> Rule | None:
        """Parse a rule file.
        
        Args:
            file_path: Path to the rule file.
            scope: The scope to assign to the parsed rule.
            
        Returns:
            Parsed Rule object, or None if file doesn't exist.
            
        Raises:
            RuleParseError: If the file is too large or has invalid format.
        """
        if not file_path.exists():
            return None

        # Check file size for security
        file_size = file_path.stat().st_size
        if file_size > MAX_RULE_FILE_SIZE:
            raise RuleParseError(
                f"Rule file exceeds size limit ({file_size} > {MAX_RULE_FILE_SIZE}): {file_path}"
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise RuleParseError(f"Failed to read rule file (encoding error): {file_path}") from e
        except OSError as e:
            raise RuleParseError(f"Failed to read rule file: {file_path}") from e

        return self.parse_content(content, scope, str(file_path))

    def parse_content(
        self,
        content: str,
        scope: RuleScope,
        source_path: str | None = None,
    ) -> Rule:
        """Parse rule content string.
        
        Args:
            content: The full content of the rule file.
            scope: The scope to assign to the parsed rule.
            source_path: Optional path to the source file for reference.
            
        Returns:
            Parsed Rule object.
            
        Raises:
            RuleParseError: If the content has invalid format or missing required fields.
        """
        # Parse YAML frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise RuleParseError(
                "Missing or invalid YAML frontmatter. "
                "Rule files must start with '---' followed by YAML metadata."
            )

        frontmatter_text = match.group(1)
        metadata = self._parse_yaml(frontmatter_text)

        # Validate required fields
        if "name" not in metadata or not metadata["name"]:
            raise RuleParseError("Missing required field: name")
        if "description" not in metadata or not metadata["description"]:
            raise RuleParseError("Missing required field: description")

        # Extract Markdown content after frontmatter
        rule_content = content[match.end():].strip()

        # Parse inclusion mode
        inclusion_str = metadata.get("inclusion", "always")
        try:
            inclusion = RuleInclusion(inclusion_str)
        except ValueError:
            logger.warning(
                f"Invalid inclusion mode '{inclusion_str}', defaulting to 'always'"
            )
            inclusion = RuleInclusion.ALWAYS

        # Parse priority
        try:
            priority = int(metadata.get("priority", 50))
            if not 1 <= priority <= 100:
                logger.warning(
                    f"Priority {priority} out of range, clamping to 1-100"
                )
                priority = max(1, min(100, priority))
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid priority value '{metadata.get('priority')}', defaulting to 50"
            )
            priority = 50

        # Parse boolean fields
        override = self._parse_bool(metadata.get("override", "false"))
        enabled = self._parse_bool(metadata.get("enabled", "true"))

        return Rule(
            name=metadata["name"],
            description=metadata["description"],
            content=rule_content,
            scope=scope,
            inclusion=inclusion,
            file_match_pattern=metadata.get("fileMatchPattern"),
            priority=priority,
            override=override,
            enabled=enabled,
            source_path=source_path,
            metadata=metadata,
        )

    def _parse_yaml(self, yaml_content: str) -> dict[str, Any]:
        """Parse simple YAML key-value pairs.
        
        This is a simple parser that handles single-level key-value pairs.
        For complex YAML, consider using PyYAML.
        
        Args:
            yaml_content: YAML content string.
            
        Returns:
            Dictionary of parsed key-value pairs.
        """
        result: dict[str, Any] = {}
        
        for line in yaml_content.split("\n"):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Match key: value pattern
            match = re.match(r"^(\w+):\s*(.*)$", line)
            if match:
                key, value = match.groups()
                # Strip quotes from value
                value = value.strip().strip('"').strip("'")
                result[key] = value
        
        return result

    def _parse_bool(self, value: str | bool) -> bool:
        """Parse a boolean value from string.
        
        Args:
            value: String or boolean value.
            
        Returns:
            Boolean interpretation of the value.
        """
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "yes", "1", "on")

    def resolve_file_references(
        self,
        content: str,
        base_path: Path,
        allowed_dirs: list[Path],
    ) -> str:
        """Resolve file references in rule content.
        
        Replaces #[[file:path]] references with the content of the referenced files.
        
        Args:
            content: Rule content with potential file references.
            base_path: Base path for resolving relative references.
            allowed_dirs: List of directories that are allowed for file references.
            
        Returns:
            Content with file references resolved.
        """
        def replace_reference(match: re.Match) -> str:
            ref_path = match.group(1).strip()
            
            # Resolve the full path
            if Path(ref_path).is_absolute():
                full_path = Path(ref_path)
            else:
                full_path = (base_path / ref_path).resolve()

            # Security check: ensure path is within allowed directories
            if not self._is_safe_path(full_path, allowed_dirs):
                logger.warning(f"File reference blocked (outside allowed dirs): {ref_path}")
                return f"[File reference blocked: {ref_path}]"

            # Check if file exists
            if not full_path.exists():
                logger.warning(f"Referenced file not found: {ref_path}")
                return f"[File not found: {ref_path}]"

            # Check file size
            if full_path.stat().st_size > MAX_RULE_FILE_SIZE:
                logger.warning(f"Referenced file too large: {ref_path}")
                return f"[File too large: {ref_path}]"

            # Read and return file content
            try:
                return full_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Error reading referenced file {ref_path}: {e}")
                return f"[Error reading file: {ref_path}]"

        return self.FILE_REFERENCE_PATTERN.sub(replace_reference, content)

    def _is_safe_path(self, path: Path, allowed_dirs: list[Path]) -> bool:
        """Check if a path is safely within allowed directories.
        
        Prevents directory traversal attacks by ensuring the resolved path
        is within one of the allowed directories.
        
        Args:
            path: Path to check.
            allowed_dirs: List of allowed base directories.
            
        Returns:
            True if the path is safe, False otherwise.
        """
        try:
            resolved = path.resolve()
            for allowed in allowed_dirs:
                try:
                    allowed_resolved = allowed.resolve()
                    resolved.relative_to(allowed_resolved)
                    return True
                except ValueError:
                    # Path is not relative to this allowed dir
                    continue
            return False
        except (OSError, RuntimeError):
            # Error resolving path (e.g., circular symlinks)
            return False

    def validate_content(self, content: str) -> tuple[bool, list[str], list[str]]:
        """Validate rule content without creating a Rule object.
        
        Args:
            content: Rule content to validate.
            
        Returns:
            Tuple of (is_valid, errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check for frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            errors.append("Missing or invalid YAML frontmatter")
            return False, errors, warnings

        # Parse and validate metadata
        frontmatter_text = match.group(1)
        metadata = self._parse_yaml(frontmatter_text)

        if "name" not in metadata or not metadata["name"]:
            errors.append("Missing required field: name")
        if "description" not in metadata or not metadata["description"]:
            errors.append("Missing required field: description")

        # Check inclusion mode
        inclusion_str = metadata.get("inclusion", "always")
        if inclusion_str not in ("always", "fileMatch", "manual"):
            warnings.append(f"Unknown inclusion mode: {inclusion_str}")

        # Check priority
        priority_str = metadata.get("priority")
        if priority_str:
            try:
                priority = int(priority_str)
                if not 1 <= priority <= 100:
                    warnings.append(f"Priority {priority} out of range (1-100)")
            except ValueError:
                warnings.append(f"Invalid priority value: {priority_str}")

        # Check content size
        rule_content = content[match.end():]
        if len(rule_content) > 50000:
            warnings.append("Rule content is very large, may impact performance")

        return len(errors) == 0, errors, warnings
