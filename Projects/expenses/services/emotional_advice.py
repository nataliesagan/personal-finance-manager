from collections import Counter
from decimal import Decimal


TAG_TO_MESSAGE = {
    'fast_food': 'Схоже, кафе й швидкі перекуси знову перемогли. Завтра спробуйте один домашній перекус — бюджет це запам’ятає.',
    'online_shopping': 'Онлайн-кошик дуже харизматичний, але не геній фінансової дисципліни. Дайте собі 30 хвилин паузи перед оплатою.',
    'late_night': 'Нічні покупки звучать романтично, але гаманець проти. Після 22:00 краще відкласти рішення до ранку.',
    'entertainment': 'Розваги потрібні, але бюджет не Netflix-підписка без ліміту. Спробуйте встановити собі межу на тиждень.',
}


def _sum_amount(expenses) -> Decimal:
    total = Decimal('0')
    for item in expenses:
        total += item.amount
    return total


def build_emotional_advice(today_expenses, month_emotional_expenses) -> list[str]:
    advice: list[str] = []

    today_emotional = [expense for expense in today_expenses if expense.is_emotional]
    today_total = _sum_amount(today_expenses)
    today_emotional_total = _sum_amount(today_emotional)

    if today_emotional and today_total > 0:
        share = float(today_emotional_total / today_total * 100)
        top_tag = Counter(
            expense.emotional_tag for expense in today_emotional if expense.emotional_tag != 'none'
        ).most_common(1)

        if top_tag:
            advice.append(TAG_TO_MESSAGE.get(
                top_tag[0][0],
                'Сьогодні було кілька імпульсивних витрат. Завтра краще дати собі коротку паузу перед оплатою.'
            ))

        if share >= 50:
            advice.append('Сьогодні емоційні витрати зайняли більше половини всіх витрат. День був яскравий, але бюджет пережив драму.')
        elif share >= 25:
            advice.append('Емоційні витрати сьогодні вже помітні. Ви ще контролюєте ситуацію, але кафе й маркетплейси явно стараються.')

    month_emotional = list(month_emotional_expenses)
    if len(month_emotional) >= 5:
        top_month_tag = Counter(
            expense.emotional_tag for expense in month_emotional if expense.emotional_tag != 'none'
        ).most_common(1)
        if top_month_tag:
            tag = top_month_tag[0][0]
            if tag == 'fast_food':
                advice.append('Головний герой місяця — швидка їжа. План на посилення: 2-3 заготовлені перекуси вдома.')
            elif tag == 'online_shopping':
                advice.append('Головний ризик місяця — онлайн-шопінг. Корисне правило: спершу в обране, потім у кошик.')
            elif tag == 'late_night':
                advice.append('Місяць підказує просту істину: вночі краще спати, а не купувати.')
            elif tag == 'entertainment':
                advice.append('Розваги гарні, але без ліміту легко перетворюються на дірку в бюджеті. Виділіть окрему суму на відпочинок.')

    if not advice:
        advice.append('Поки що серйозних сигналів немає. Бюджет дихає рівно, не лякайте його нічними замовленнями.')

    return advice[:3]