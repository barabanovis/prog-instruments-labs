ind = 3
h = (ind * 25 + 35) % 72
typing = (h % 2) + 1
cycle = ((h // 2) % 3) + 1
structure = ((h // 6) % 3) + 1
syntax = ((h // 18) % 4) + 1
typing_letter = 'А' if typing == 1 else 'Б'
print(f"{syntax}-{cycle}-{structure}-{typing_letter}")
# 3-2-1-А
