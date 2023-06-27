import datetime

from pyrogram import filters
from pyrogram.types import CallbackQuery, Message

from config import Config
from Music.core.clients import hellbot
from Music.core.database import db
from Music.core.decorators import UserWrapper, check_mode
from Music.helpers.formatters import formatter
from Music.utils.pages import MakePages
from Music.utils.youtube import ytube


@hellbot.app.on_message(
    filters.command(["favs", "myfavs", "favorites", "delfavs"]) & ~Config.BANNED_USERS
)
@check_mode
@UserWrapper
async def favorites(_, message: Message):
    delete = False
    hell = await message.reply_text("Fetching favorites ...")
    favs = await db.get_all_favorites(message.from_user.id)
    if not favs:
        await hell.edit_text("You dont have any favorite tracks added to the bot!")
    if message.command[0][1] == "d":
        delete = True
    await MakePages.favorite_page(hell, favs, message.from_user.id, 0, 0, True, delete)


@hellbot.app.on_callback_query(filters.regex(r"add_favorite") & ~Config.BANNED_USERS)
async def add_favorites(_, cb: CallbackQuery):
    _, video_id = cb.data.split("|")
    track = await db.get_favorite(cb.from_user.id, video_id)
    if track:
        return await cb.answer("Already in your favorites!", show_alert=True)
    count = len(await db.get_all_favorites(cb.from_user.id))
    if count == Config.MAX_FAVORITES:
        return await cb.answer(
            "You can't have more than 50 favorites!", show_alert=True
        )
    details = await ytube.get_data(video_id, True)
    context = {
        "video_id": details["id"],
        "title": details["title"],
        "duration": details["duration"],
        "add_date": datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
    }
    await db.add_favorites(cb.from_user.id, video_id, context)
    await cb.answer(
        f"Added to your favorites!\n\n{details['title'][:50]}", show_alert=True
    )


@hellbot.app.on_callback_query(filters.regex(r"myfavs") & ~Config.BANNED_USERS)
async def myfavs_cb(_, cb: CallbackQuery):
    _, action, user_id, page = cb.data.split("|")
    if int(user_id) != cb.from_user.id:
        return await cb.answer("This is not for you!", show_alert=True)
    if action == "close":
        await cb.message.delete()
        await cb.answer("Closed!", show_alert=True)
    else:
        collection = await db.get_all_favorites(int(user_id))
        last_page, _ = formatter.group_the_list(collection, length=True)
        last_page -= 1
        if int(page) == 0 and action == "prev":
            new_page = last_page
        elif int(page) == last_page and action == "next":
            new_page = 0
        else:
            new_page = int(page) + 1 if action == "next" else int(page) - 1
        index = new_page * 7
        await MakePages.favorite_page(cb, collection, int(user_id), new_page, index, True)


@hellbot.app.on_callback_query(filters.regex(r"delfavs") & ~Config.BANNED_USERS)
async def delfavs_cb(_, cb: CallbackQuery):
    _, action, user_id = cb.data.split("|")
    if int(user_id) != cb.from_user.id:
        return await cb.answer("This is not for you!", show_alert=True)
    collection = await db.get_all_favorites(int(user_id))
    if action == "all":
        for i in collection:
            await db.rem_favorites(int(user_id), i["video_id"])
        return await cb.message.edit_text("Deleted all your favorites!")
    else:
        is_deleted = await db.rem_favorites(int(user_id), action)
        if is_deleted:
            await cb.answer("Deleted from your favorites!", show_alert=True)
            collection = await db.get_all_favorites(int(user_id))
            await MakePages.favorite_page(cb, collection, int(user_id), 0, 0, True, True)
        else:
            await cb.answer("Not in your favorites!", show_alert=True)
