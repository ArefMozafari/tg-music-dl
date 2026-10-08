"""Downloads the newest not-yet-downloaded media from one channel."""
import os

from tg_music_dl.media import file_name, media_type

# Marks a file still being written; it is renamed only once complete.
PARTIAL_SUFFIX = ".part"
BYTES_PER_MEGABYTE = 1024 * 1024


def print_progress(received, total):
    """Prints download progress in place: percentage and size when the total is known."""
    received_megabytes = received / BYTES_PER_MEGABYTE
    if total:
        total_megabytes = total / BYTES_PER_MEGABYTE
        print(f"\r  {100 * received / total:.1f}% ({received_megabytes:.2f} / {total_megabytes:.2f} MB)",
              end="", flush=True)
    else:
        print(f"\r  {received_megabytes:.2f} MB", end="", flush=True)


def find_target(path, size):
    """Returns where a file of `size` bytes belongs, and whether it is already there.

    A same-sized file at `path`, or at one of its "name (n).ext" variants, is
    taken to be this file. Otherwise the first free variant is returned, so a
    different song that shares the name is never skipped or overwritten.
    """
    stem, extension = os.path.splitext(path)
    candidate, number = path, 1
    while os.path.exists(candidate):
        if os.path.getsize(candidate) == size:
            return candidate, True
        candidate = f"{stem} ({number}){extension}"
        number += 1
    return candidate, False


async def download_channel(client, entity, channel_key, output, limit, types, state):
    """Downloads up to `limit` new files of the given media types from one channel, newest first.

    Skips messages already recorded in `state`, and records files already on
    disk without fetching them again. Each file is written under a .part name
    and renamed once complete, so an interrupted download never passes for a
    finished one. Returns how many files were downloaded.
    """
    downloaded_count = 0
    async for message in client.iter_messages(entity):
        if downloaded_count >= limit:
            break
        # Skips messages without media of a requested type, such as photos and
        # other files, and messages an earlier run already downloaded.
        if media_type(message) not in types or state.has(channel_key, message.id):
            continue
        target, already_there = find_target(os.path.join(output, file_name(message)), message.file.size)
        name = os.path.basename(target)
        if already_there:
            # Downloaded before the state file knew about it, e.g. by an older version.
            print("Already downloaded:", name)
            state.add(channel_key, message.id)
            continue
        print("Downloading:", name)
        partial = await client.download_media(message, file=target + PARTIAL_SUFFIX,
                                              progress_callback=print_progress)
        # Ends the progress line.
        print()
        os.replace(partial, target)
        state.add(channel_key, message.id)
        downloaded_count += 1
    return downloaded_count
