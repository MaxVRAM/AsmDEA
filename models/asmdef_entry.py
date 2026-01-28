"""Data models for Assembly Definition entries."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class AsmdefEntry:
    """Represents a Unity Assembly Definition file entry.

    Attributes:
        guid: Unique identifier (e.g., "GUID:abc123...")
        name: Assembly name from the .asmdef file
        references: List of GUID references to other assemblies
        file_path: Path to the .asmdef file
        root_namespace: Root namespace defined in assembly (if any)
        include_platforms: List of platforms to include
        exclude_platforms: List of platforms to exclude
        allow_unsafe_code: Whether unsafe code is allowed
        override_references: Whether to override references
        precompiled_references: List of precompiled assembly references
        auto_referenced: Whether assembly is auto-referenced
        define_constraints: Define constraints for this assembly
        version_defines: Version defines for this assembly
        no_engine_references: Whether to exclude engine references
        raw_data: Original JSON data from .asmdef file
    """

    guid: str
    name: str
    file_path: Path
    references: List[str] = field(default_factory=list)
    root_namespace: Optional[str] = None
    include_platforms: List[str] = field(default_factory=list)
    exclude_platforms: List[str] = field(default_factory=list)
    allow_unsafe_code: bool = False
    override_references: bool = False
    precompiled_references: List[str] = field(default_factory=list)
    auto_referenced: bool = True
    define_constraints: List[str] = field(default_factory=list)
    version_defines: List[Dict[str, Any]] = field(default_factory=list)
    no_engine_references: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, guid: str, data: Dict[str, Any], file_path: Path) -> "AsmdefEntry":
        """Create AsmdefEntry from dictionary data.

        Args:
            guid: Assembly GUID
            data: Dictionary from parsed .asmdef JSON
            file_path: Path to the .asmdef file

        Returns:
            AsmdefEntry instance
        """
        return cls(
            guid=guid,
            name=data.get("name", ""),
            file_path=file_path,
            references=data.get("references", []),
            root_namespace=data.get("rootNamespace"),
            include_platforms=data.get("includePlatforms", []),
            exclude_platforms=data.get("excludePlatforms", []),
            allow_unsafe_code=data.get("allowUnsafeCode", False),
            override_references=data.get("overrideReferences", False),
            precompiled_references=data.get("precompiledReferences", []),
            auto_referenced=data.get("autoReferenced", True),
            define_constraints=data.get("defineConstraints", []),
            version_defines=data.get("versionDefines", []),
            no_engine_references=data.get("noEngineReferences", False),
            raw_data=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert AsmdefEntry back to dictionary format.

        Returns:
            Dictionary compatible with .asmdef JSON format
        """
        result = {
            "name": self.name,
            "references": self.references,
        }

        if self.root_namespace:
            result["rootNamespace"] = self.root_namespace
        if self.include_platforms:
            result["includePlatforms"] = self.include_platforms
        if self.exclude_platforms:
            result["excludePlatforms"] = self.exclude_platforms
        if self.allow_unsafe_code:
            result["allowUnsafeCode"] = self.allow_unsafe_code
        if self.override_references:
            result["overrideReferences"] = self.override_references
        if self.precompiled_references:
            result["precompiledReferences"] = self.precompiled_references
        if not self.auto_referenced:
            result["autoReferenced"] = self.auto_referenced
        if self.define_constraints:
            result["defineConstraints"] = self.define_constraints
        if self.version_defines:
            result["versionDefines"] = self.version_defines
        if self.no_engine_references:
            result["noEngineReferences"] = self.no_engine_references

        return result
