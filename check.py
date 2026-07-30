import pygame
import random
import sys
from collections import deque

# ================== НАСТРОЙКИ ==================
GRID_SIZE = 32
TILE = 22
WIDTH = HEIGHT = GRID_SIZE * TILE
FPS = 60

# Цвета
BG = (34, 48, 36)
GRID_COLOR = (45, 62, 48)
PLAYER_COLOR = (255, 220, 180)
PIG_COLOR = (255, 150, 180)
CRACK_COLOR = (20, 15, 10)
CRACK_EDGE = (80, 50, 30)
TEXT_COLOR = (220, 230, 200)

# ================== КЛАССЫ ==================
class Entity:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dir = (0, 1)  # вниз по умолчанию

    def pos(self):
        return self.x, self.y

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.kick_cooldown = 0

    def move(self, dx, dy, cracks, pigs):
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            if (nx, ny) not in cracks:
                # Нельзя наступать на свинью
                if not any(p.x == nx and p.y == ny for p in pigs):
                    self.x, self.y = nx, ny
                    if dx or dy:
                        self.dir = (dx, dy)

    def kick(self, cracks):
        if self.kick_cooldown > 0:
            return
        fx = self.x + self.dir[0]
        fy = self.y + self.dir[1]
        if 0 <= fx < GRID_SIZE and 0 <= fy < GRID_SIZE:
            cracks.add((fx, fy))
            self.kick_cooldown = 15  # небольшая задержка между ударами

class Pig(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.move_timer = 0
        self.speed = random.randint(12, 18)  # чем меньше — тем быстрее

    def update(self, player, cracks, pigs, walls):
        self.move_timer += 1
        if self.move_timer < self.speed:
            return True  # ещё жива

        self.move_timer = 0

        # Простая погоня: выбираем направление ближе к игроку
        dx = 0
        dy = 0
        if abs(player.x - self.x) > abs(player.y - self.y):
            dx = 1 if player.x > self.x else -1
        else:
            dy = 1 if player.y > self.y else -1

        # Иногда случайно меняем направление (чтобы не застревали)
        if random.random() < 0.15:
            dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            dx, dy = random.choice(dirs)

        nx, ny = self.x + dx, self.y + dy

        # Проверка границ и препятствий
        if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
            return True
        if (nx, ny) in cracks:
            return False  # упала в трещину — смерть
        if any(p.x == nx and p.y == ny for p in pigs if p is not self):
            return True
        if (nx, ny) == (player.x, player.y):
            return True  # пока просто не наступаем на игрока

        self.x, self.y = nx, ny
        self.dir = (dx, dy)
        return True

# ================== ОТРИСОВКА ==================
def draw_player(screen, p):
    cx = p.x * TILE + TILE // 2
    cy = p.y * TILE + TILE // 2
    # тело
    pygame.draw.circle(screen, PLAYER_COLOR, (cx, cy - 2), 7)
    # голова
    pygame.draw.circle(screen, (255, 200, 160), (cx, cy - 9), 5)
    # нога в направлении удара
    fx = cx + p.dir[0] * 6
    fy = cy + p.dir[1] * 6 + 2
    pygame.draw.line(screen, (180, 140, 100), (cx, cy + 2), (fx, fy), 3)

def draw_pig(screen, pig):
    cx = pig.x * TILE + TILE // 2
    cy = pig.y * TILE + TILE // 2
    # тело
    pygame.draw.ellipse(screen, PIG_COLOR, (cx - 9, cy - 6, 18, 13))
    # голова
    pygame.draw.circle(screen, (255, 170, 190), (cx + pig.dir[0] * 6, cy - 2), 6)
    # пятачок
    pygame.draw.circle(screen, (255, 120, 150), (cx + pig.dir[0] * 9, cy - 1), 3)
    # ушки
    pygame.draw.polygon(screen, (255, 140, 170), [
        (cx - 4, cy - 8), (cx - 7, cy - 13), (cx - 1, cy - 10)
    ])
    pygame.draw.polygon(screen, (255, 140, 170), [
        (cx + 4, cy - 8), (cx + 7, cy - 13), (cx + 1, cy - 10)
    ])

def draw_crack(screen, x, y):
    cx = x * TILE + TILE // 2
    cy = y * TILE + TILE // 2
    # основная трещина
    pygame.draw.line(screen, CRACK_COLOR, (cx - 8, cy - 3), (cx + 9, cy + 4), 3)
    pygame.draw.line(screen, CRACK_COLOR, (cx - 5, cy + 6), (cx + 6, cy - 7), 2)
    # края
    pygame.draw.line(screen, CRACK_EDGE, (cx - 8, cy - 3), (cx + 9, cy + 4), 1)

def draw_grid(screen):
    for i in range(GRID_SIZE + 1):
        pygame.draw.line(screen, GRID_COLOR, (i * TILE, 0), (i * TILE, HEIGHT), 1)
        pygame.draw.line(screen, GRID_COLOR, (0, i * TILE), (WIDTH, i * TILE), 1)

# ================== ГЛАВНЫЙ ЦИКЛ ==================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Трещины и Свиньи — мини-Бомбермен")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    # Стартовая позиция игрока — центр
    player = Player(GRID_SIZE // 2, GRID_SIZE // 2)
    cracks = set()
    pigs = []
    spawn_timer = 0
    score = 0
    game_over = False

    # Начальные свиньи
    for _ in range(3):
        while True:
            x, y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
            if abs(x - player.x) > 6 or abs(y - player.y) > 6:
                pigs.append(Pig(x, y))
                break

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if game_over and event.key == pygame.K_r:
                    # рестарт
                    return main()

        if not game_over:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            elif keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1

            if dx or dy:
                player.move(dx, dy, cracks, pigs)

            if keys[pygame.K_SPACE]:
                player.kick(cracks)

            if player.kick_cooldown > 0:
                player.kick_cooldown -= 1

            # Обновление свиней
            alive_pigs = []
            for pig in pigs:
                still_alive = pig.update(player, cracks, pigs, None)
                if still_alive:
                    alive_pigs.append(pig)
                else:
                    score += 1
            pigs = alive_pigs

            # Спавн новых свиней (макс 5)
            spawn_timer += 1
            if len(pigs) < 5 and spawn_timer > 90:
                spawn_timer = 0
                for _ in range(20):
                    x = random.randint(0, GRID_SIZE - 1)
                    y = random.randint(0, GRID_SIZE - 1)
                    if (x, y) not in cracks and (x, y) != (player.x, player.y):
                        if abs(x - player.x) + abs(y - player.y) > 8:
                            pigs.append(Pig(x, y))
                            break

            # Проверка столкновения со свиньёй
            for pig in pigs:
                if pig.x == player.x and pig.y == player.y:
                    game_over = True

        # ===== РИСОВАНИЕ =====
        screen.fill(BG)
        draw_grid(screen)

        for cx, cy in cracks:
            draw_crack(screen, cx, cy)

        for pig in pigs:
            draw_pig(screen, pig)

        draw_player(screen, player)

        # Интерфейс
        score_surf = font.render(f"Свиней свалило: {score}", True, TEXT_COLOR)
        pigs_surf = font.render(f"Свиней на поле: {len(pigs)}/5", True, TEXT_COLOR)
        screen.blit(score_surf, (10, 8))
        screen.blit(pigs_surf, (10, 28))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            go_text = font.render("СВИНЬИ ТЕБЯ ДОГНАЛИ!", True, (255, 100, 100))
            restart = font.render("Нажми R чтобы начать заново", True, TEXT_COLOR)
            screen.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 30))
            screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
