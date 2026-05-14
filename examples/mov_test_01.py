import av

path = "/run/media/batman/ALPHA/works/C2C/samples/footage/Timeline_1.mp4"
# path = "/run/media/batman/ALPHA/works/C2C/samples/footage/Timeline_4.mp4"

container = av.open(path)
stream = container.streams.video[0]

frame_count = stream.frames

print("frame_count", frame_count)

# frame_generator = container.decode(stream)

# print("\n", frame_generator)

# frame = next(frame_generator)

# print("\nframe", frame)


# Got It, how to intagrated this concept in player.load and update_frame in player module

# stream = container.streams.video[0]

# print(len(container.decode(stream)))
# frames = [frame for frame in container.decode(stream)]
# print(frames)
