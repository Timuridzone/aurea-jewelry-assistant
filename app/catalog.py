import re
import unicodedata
from sqlalchemy import select
from .db import Product


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


ALIASES = {
    'category': {'anillo': ['anillo', 'ring', 'alianza', 'compromiso'], 'pendientes': ['pendiente', 'earring'], 'collar': ['collar', 'necklace', 'colgante'], 'pulsera': ['pulsera', 'bracelet'], 'reloj': ['reloj', 'watch']},
    'material': {'oro': ['oro', 'gold'], 'plata': ['plata', 'silver'], 'acero': ['acero', 'steel'], 'titanio': ['titanio', 'titanium']},
    'style': {'minimalista': ['minimal', 'sencill', 'simple'], 'clasico': ['clasic', 'classic', 'elegant'], 'moderno': ['modern', 'contempor'], 'romantico': ['romantic', 'corazon'], 'vintage': ['vintage', 'retro']},
}


def extract_preferences(text, previous=None):
    result = dict(previous or {})
    t = normalize(text)
    if any(x in t for x in ['empezar de nuevo', 'sin filtros', 'reset preferences', 'clear filters']):
        result = {}
    for field, values in ALIASES.items():
        matches = [(t.find(word), key) for key, words in values.items() for word in words if word in t]
        if matches:
            result[field] = sorted(matches)[-1][1]
    # Parse currency and explicit budgets, never order/reference numbers.
    amount = r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)'
    found = re.search(amount + r'\s*(?:€|euros?|eur\b)', t)
    if not found:
        found = re.search(r'(?:presupuesto|budget|hasta|menos de|under|maximo|max|up to)\s*(?:de|of|is|es|:)?\s*€?\s*' + amount, t)
    if found:
        number = found.group(1)
        if re.fullmatch(r'\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?', number):
            number = number.replace('.', '')
        result['budget'] = min(1000000, float(number.replace(',', '.')))
    if 'sin presupuesto' in t or 'no budget' in t:
        result.pop('budget', None)
    return result


def recommend(session, preferences, limit=4):
    q = select(Product).where(Product.available.is_(True))
    for field in ('category', 'material', 'style'):
        if preferences.get(field):
            q = q.where(getattr(Product, field) == preferences[field])
    if preferences.get('budget') is not None:
        q = q.where(Product.price_cents <= round(preferences['budget'] * 100))
    products = list(session.scalars(q))
    # Within the hard constraints, favor pieces closest to the stated budget.
    products.sort(key=lambda p: (abs(preferences['budget'] * 100 - p.price_cents) if preferences.get('budget') is not None else p.price_cents, p.id))
    return products[:limit]


def product_dict(p):
    return {'id': p.id, 'name': p.name, 'category': p.category, 'price': p.price_cents / 100, 'material': p.material, 'style': p.style, 'description': p.description, 'available': p.available}
