"""Map each real PII value to one stable fake stand-in.

Fakes use reserved / documentation ranges so they are clearly not real:
TEST-NET IPs, example.com emails, invalid SSN area/group numbers.
"""
from __future__ import annotations
import hashlib
import re
from faker import Faker
EXAMPLE_IPV4 = '192.0.2.{}'
EXAMPLE_IPV6 = '2001:db8::{:x}'

def _seeded_faker(value: str, pii_type: str) -> Faker:
    digest = hashlib.sha256(f'{pii_type}::{value.lower()}'.encode()).hexdigest()
    fake = Faker()
    fake.seed_instance(int(digest[:16], 16) % 2 ** 31)
    return fake

def fake_for(value: str, pii_type: str, used: set) -> str:
    """Return a fake replacement; retry until it is unique in this run."""
    fake = _seeded_faker(value, pii_type)
    for _ in range(25):
        candidate = _generate(fake, value, pii_type)
        key = (pii_type, candidate.lower())
        if key not in used:
            used.add(key)
            return candidate
        fake.unique.clear()
        fake.seed_instance(fake.random_int(0, 2 ** 31 - 1))
    return _generate(fake, value, pii_type)

def _generate(fake: Faker, value: str, pii_type: str) -> str:
    if pii_type == 'name':
        if value.isupper() and len(value) > 3:
            return fake.name().upper()
        return fake.name()
    if pii_type == 'email':
        local = re.sub('[^a-z0-9.]+', '.', fake.user_name().lower())
        return f'{local}@example.com'
    if pii_type == 'phone':
        digits = re.sub('\\D', '', value)
        if digits.startswith('1') and len(digits) == 11:
            return f'+1 555 {fake.random_int(100, 899):03d} {fake.random_int(1000, 9999)}'
        if digits.startswith('91') and len(digits) > 10:
            rest = f'{fake.random_int(10, 99)} {fake.random_int(1000, 9999)} {fake.random_int(1000, 9999)}'
            prefix = '+91 ' if value.strip().startswith('+') else '91 '
            return prefix + rest
        return f'+91 {fake.random_int(6000000000, 9999999999)}'
    if pii_type == 'company':
        suffix = 'Limited'
        lower = value.lower()
        if 'trust' in lower:
            return f'{fake.last_name()} Family Trust'
        if 'llp' in lower:
            return f'{fake.last_name()} & {fake.last_name()} LLP'
        if 'llc' in lower:
            return f'{fake.last_name()} LLC'
        if 'private' in lower or 'pvt' in lower:
            suffix = 'Private Limited'
        if 'bank' in lower:
            return f'{fake.last_name()} Bank Limited'
        name = fake.company().replace(',', '')
        return f'{name} {suffix}' if suffix.lower() not in name.lower() else name
    if pii_type == 'address':
        return f'{fake.building_number()}, Example Street, {fake.city()}, {fake.random_int(100000, 999999)}, India'
    if pii_type == 'ssn':
        hyphenated = '-' in value
        serial = fake.random_int(1, 9999)
        if hyphenated:
            return f'000-00-{serial:04d}'
        return f'00000{serial:04d}'
    if pii_type == 'credit_card':
        return f'4111-1111-1111-{fake.random_int(1000, 9999):04d}'
    if pii_type == 'dob':
        if re.fullmatch('\\d{4}-\\d{2}-\\d{2}', value.strip()):
            return fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%Y-%m-%d')
        if re.search('[A-Za-z]', value):
            return fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%d %B %Y')
        return fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%d/%m/%Y')
    if pii_type == 'ip':
        if ':' in value:
            return EXAMPLE_IPV6.format(fake.random_int(1, 65535))
        return EXAMPLE_IPV4.format(fake.random_int(1, 254))
    return '[REDACTED]'