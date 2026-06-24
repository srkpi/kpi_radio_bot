import operator
from typing import Any

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, StartMode, Window, DialogManager
from aiogram_dialog.widgets.kbd import Select, Column, Start
from aiogram_dialog.widgets.text import Const, Case, Format

from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates

order = Const("""
📝 *Аби замовити пісню треба:*

- натиснути на кнопку Замовити пісню;
- надіслати боту посилання на пісню з YouTube Music або Spotify;
- вибрати день та час для замовлення.
""")

moderation = Const("""
✅ В пріоритеті — спокійна музика, яка не відволікатиме від освітнього процесу. Вітаються українські пісні, цінуємо своє!

⚠️ *Обмеження на кількість треків:*
- не більше 2 треків на перерву (ранковий / денні перерви);
- не більше 4–5 треків на вечірній етер;
- треки довжиною понад 5 хвилин на перервах проходять ручну модерацію навіть якщо автоматично схвалені.

❌ *Відхиляємо:*
- треки довжиною менше хвилини;
- треки довжиною понад 6 хвилин;
- лайви, bass boosted версії, ремікси поганої якості;
- повторно замовлений трек на ту саму перерву; 
- треки з нецензурною лексикою та непристойним змістом;
- не формат радіо (див. нижче).

*Модератори однозначно не є поціновувачами:*
- будь-чого російською/від росіян;
- треків з елементами скріму та жорсткого металу;
- гачі та стогонів;
- каверів;
- виконавців з сумнівною репутацією.

❗️ Пам'ятай, рупора радіо – не колонки у клубі.
Модератори мають право відхилити трек без пояснення причин :3
""")

playlist = Const("""
⏭️ *Плейлист радіо:*

- Дізнатися, що грає зараз, грало до цього або буде грати, можна натиснувши на кнопку "Що грає";
- Замовлення — одноразове. Якщо твоя пісня з якихось причин не зазвучала — перезамов наступної перерви.
""")

support = Const("""
🖌 *Зворотний звʼязок:*

- Ти завжди можеш написати команді, що думаєш про них і про радіо (звісно, якщо це не порушує кримінальний кодекс України).

- Якщо хочеш стати частиною радіо, пиши про це і готуйся до співбесід 😈

- В разі наявності пропозицій щодо будь-яких покращень чи вдосконалень — завжди можеш про це повідомити.

- А ще — в нас є чатик @rhub\\_kpi 😉
""")


async def get_data(dialog_manager: DialogManager, **kwargs):
    help_items = [
        ("📝 Замовлення пісні", "1"),
        ("❗️ Модерація", "2"),
        ("⏭ Плейліст", "3"),
        ("🖌 Зворотний звʼязок", "4"),
    ]

    selected_id = dialog_manager.dialog_data.get("help_id")
    filtered_help_items = [item for item in help_items if item[1] != selected_id]

    return {"help": filtered_help_items}


async def on_help_menu_selected(
    callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str
):
    manager.dialog_data["help_id"] = item_id


help_menu = Dialog(
    Window(
        Case(
            {
                "1": order,
                "2": moderation,
                "3": playlist,
                "4": support,
                ...: Const("Вибери тему, що тебе цікавить. (Радимо прочитати все)"),
            },
            selector=F["dialog_data"]["help_id"],
        ),
        Column(
            Select(
                Format("{item[0]}"),
                id="s_help",
                item_id_getter=operator.itemgetter(1),
                items="help",
                on_click=on_help_menu_selected,
            ),
            Start(
                text=Const("Назад"),
                id="__main__",
                state=MainStates.main,
                mode=StartMode.RESET_STACK,
            ),
        ),
        state=HelpStates.select,
        getter=get_data,
        parse_mode="Markdown",
    )
)
