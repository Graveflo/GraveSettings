# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, MutableMapping, Type, Iterable

VALIDATION_FIX_SIGNATURE = Callable[[MutableMapping, str], bool]
VALIDATION_FUNCTION_SIGNATURE = Callable[[MutableMapping, str, ...], VALIDATION_FIX_SIGNATURE | None]


@dataclass(slots=True, frozen=True)
class ValidationReport(object):
    settings: MutableMapping
    settings_key: str
    name: str
    description: str
    long_description: str
    fixes: list[VALIDATION_FIX_SIGNATURE] | None = None


class Validation:
    def __init__(self, key: str):
        self.settings_key = key

    def validate(self, settings: MutableMapping, settings_key: str) -> ValidationReport | None:
        return None

    def make_validation_report(self, *args):
        return ValidationReport(*args)


class ValidationCapsule(Validation):
    validate: VALIDATION_FUNCTION_SIGNATURE
    make_validation_report: Callable[..., ValidationReport] = ValidationReport


class NotNoneValidation(Validation):
    def validate(self, settings: MutableMapping, settings_key: str) -> ValidationReport | None:
        if settings[settings_key] is None:
            return self.make_validation_report(settings, settings_key, 'NoneType Error',
                                               'Parameter has a value of None',
                                               f'Parameter {settings_key} in settings object {settings} has a value of None')


class TypeCheckValidation(Validation):
    def __init__(self, key: str, _type: Type):
        super().__init__(key)
        self.check_type = _type

    def validate(self, settings: MutableMapping, settings_key: str) -> ValidationReport | None:
        sot = type(settings[settings_key])
        check_type = self.check_type
        if sot is not check_type:
            return ValidationReport(settings, settings_key, 'TypeError',
                                    f'Parameter is expected to be {check_type.__class__.__name__}',
                                    (f'Parameter {settings_key} of {settings} is expected to be of type {check_type}, '
                                     'but instead is of type {sot}'))


class SettingsValidator(object):
    def __init__(self, settings: MutableMapping):
        self.settings = settings
        self.validations: list[Validation] = []

    def create_validation(self, name: str, validation_function: VALIDATION_FUNCTION_SIGNATURE,
                          v_t: Type[Validation] = Validation):
        self.add_validation(v_t(name, validation_function))

    def create_validations(self, validations: list[tuple[str, VALIDATION_FUNCTION_SIGNATURE]],
                           v_t: Type[Validation] = Validation):
        self.add_validations(v_t(*x) for x in validations)

    def add_validation(self, validation: Validation):
        self.validations.append(validation)

    def add_validations(self, validations: Iterable[Validation]):
        self.validations.extend(validations)

    def get_validation_issues(self) -> dict:
        issues = defaultdict(list)
        for validation in self.validations:
            settings_key = validation.settings_key
            if vr := validation.validate(self.settings, settings_key):
                issues[settings_key].append(vr)
        return issues

