from collections import Counter
from decimal import Decimal

TAG_TO_MESSAGE = {
    'fast_food': 'Схоже, кафе, десерти й швидкі перекуси сьогодні дуже старалися. Спробуйте завтра підготувати один домашній перекус — бюджет це оцінить.',
    'online_shopping': 'Онлайн-кошик поводиться занадто харизматично. Перед наступною оплатою дайте собі 30 хвилин паузи.',
    'late_night': 'Нічні покупки звучать романтично, але гаманець проти. Після 21:00 краще відкласти рішення до ранку.',
    'entertainment': 'Розваги потрібні, але без ліміту вони легко стають фінансовою драмою. Спробуйте встановити межу на тиждень.',
}

TAG_TO_MONTH_MESSAGE = {
    'fast_food': 'Головний герой місяця — кава, десерти або швидка їжа. План на посилення: 2-3 перекуси вдома замість випадкових покупок.',
    'online_shopping': 'Головний ризик місяця — онлайн-шопінг. Корисне правило: спершу в обране, потім у кошик, а оплачувати тільки наступного дня.',
    'late_night': 'Місяць підказує просту істину: вночі краще спати, а не купувати. Бюджет теж за здоровий сон.',
    'entertainment': 'Розваги гарні, але без ліміту швидко перетворюються на дірку в бюджеті. Виділіть окрему суму на відпочинок.',
}


def _sum_amount(expenses) -> Decimal:
    total = Decimal('0')
    for item in expenses:
        total += item.amount
    return total


def build_emotional_advice(today_expenses, month_emotional_expenses) -> list[str]:
    advice: list[str] = []

    today_expenses = list(today_expenses)
    month_emotional = list(month_emotional_expenses)
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

    if len(month_emotional) >= 5:
        top_month_tag = Counter(
            expense.emotional_tag for expense in month_emotional if expense.emotional_tag != 'none'
        ).most_common(1)
        if top_month_tag:
            advice.append(TAG_TO_MONTH_MESSAGE.get(
                top_month_tag[0][0],
                'За місяць накопичилися повторювані емоційні витрати. Варто встановити невеликий ліміт саме на цю групу.'
            ))

    if not advice:
        advice.append('Поки що серйозних сигналів немає. Бюджет дихає рівно, не лякайте його нічними замовленнями.')

    return advice[:3]
