"""Loads and validates the field dictionary (packages/rules/fields.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from renova_extract.fields.normalize import NORMALIZERS

Method = Literal["label", "block", "above", "title_number", "address", "signature"]
DOC_TYPES = {
    "wniosek_ekstrakt",
    "oferta",
    "umowa",
    "aneks",
    "faktura",
    "faktura_zaliczkowa",
    "faktura_korygujaca",
    "protokol_odbioru",
    "karta_produktu",
}


class ExtractRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Method
    anchors: tuple[str, ...] = ()

    @field_validator("anchors")
    @classmethod
    def _longest_first(cls, anchors: tuple[str, ...]) -> tuple[str, ...]:
        # "razem vat" must win over "vat" when both are present on a page.
        return tuple(sorted(anchors, key=lambda a: len(a.split()), reverse=True))


class FieldSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: str
    label_pl: str
    documents: tuple[str, ...]
    extract: tuple[ExtractRule, ...]

    @field_validator("type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        if value not in NORMALIZERS:
            raise ValueError(f"unknown field type {value!r}")
        return value

    @field_validator("documents")
    @classmethod
    def _known_documents(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = set(value) - DOC_TYPES
        if unknown:
            raise ValueError(f"unknown document types {sorted(unknown)}")
        return value


class FieldDictionary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    fields: tuple[FieldSpec, ...]

    @classmethod
    def from_yaml(cls, path: Path) -> FieldDictionary:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        specs = [{"name": name, **spec} for name, spec in raw["fields"].items()]
        return cls(version=raw["version"], fields=tuple(FieldSpec.model_validate(s) for s in specs))

    def get(self, name: str) -> FieldSpec:
        for spec in self.fields:
            if spec.name == name:
                return spec
        raise KeyError(name)

    def fields_for(self, doc_type: str | None) -> list[FieldSpec]:
        """Fields read from a document of this type; all fields when the type is unknown."""
        return [f for f in self.fields if doc_type is None or doc_type in f.documents]
