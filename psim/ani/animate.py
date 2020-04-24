#! /usr/bin/env python

import psim.ani

from psim.ani import *

import pygame
import pygame.gfxdraw

# Import pygame.locals for easier access to key coordinates
from pygame.locals import (
    K_SPACE,
    K_ESCAPE,
    K_DOWN,
    K_UP,
    K_RIGHT,
    K_LEFT,
    KEYDOWN,
    KEYUP,
    QUIT,
)

import numpy as np


class Ball(pygame.sprite.Sprite):
    def __init__(self, ball, rvw_history, scale, trace=True):
        """A ball sprite

        Parameters
        ==========
        ball : psim.objects.Ball
        """
        self.scale = scale
        self.id = ball.id
        self._ball = ball
        self.radius = d_to_px(ball.R, self.scale)

        self.rvw_history = rvw_history
        self.xs = d_to_px(scale, self.rvw_history[:,0,0])
        self.ys = d_to_px(scale, self.rvw_history[:,0,1])

        super(Ball, self).__init__()

        self.color = BALL_RGB.get(self.id, (255,255,255))

        self.trace = trace
        self.trace_length = TRACE_LENGTH

        # See https://www.reddit.com/r/pygame/comments/6v9os5/how_to_draw_a_sprite_with_a_circular_shape/
        # for anti-aliased version if you don't like this later
        self.surf = pygame.Surface((2*self.radius, 2*self.radius), pygame.SRCALPHA)
        pygame.draw.circle(
            self.surf,
            self.color,
            (self.radius, self.radius),
            self.radius
        )
        self.rect = self.surf.get_rect()

        self.update(frame=0)


    def update(self, frame):
        self.rect.center = (
            self.xs[frame],
            self.ys[frame],
        )


class AnimateShot(object):
    def __init__(self, shot, size=None, cloth_color=None, rail_color=None, edge_color=None):
        """Animate a shot in pygame

        Parameters
        ==========
        shot : psim.engine.ShotSimulation

        size : int
            size in pixels of largest dimension of screen
        """

        self.size = size or MAX_SCREEN
        self.cloth_color = cloth_color or CLOTH_RGB
        self.rail_color = rail_color or RAIL_CLOTH_RGB
        self.edge_color = edge_color or EDGE_RGB

        self.shot = shot
        self.table = shot.table
        self.balls = shot.balls
        self.times = shot.get_time_array()
        self.num_frames = shot.n

        self.table_x, self.table_y = self.calculate_table_size()
        self.surface_x, self.surface_y = self.calculate_playing_surface()
        self.scale = self.size / max([self.table_x, self.table_y])

        self.px = {
            'rail': d_to_px(self.scale, self.table.rail_width),
            'edge': d_to_px(self.scale, self.table.edge_width),
            'table_x': d_to_px(self.scale, self.table_x),
            'table_y': d_to_px(self.scale, self.table_y),
            'surface_x': d_to_px(self.scale, self.surface_x),
            'surface_y': d_to_px(self.scale, self.surface_y),
            'diamond': d_to_px(self.scale, psim.diamond_size),
        }
        self.px['offset_x'] = (self.px['table_x'] - self.px['surface_x'])/2
        self.px['offset_y'] = (self.px['table_y'] - self.px['surface_y'])/2

        pygame.init()

        self.screen = pygame.display.set_mode((self.px['table_x'], self.px['table_y']))

        self.init_ball_sprites()

        self.clock = pygame.time.Clock()
        self.fps = self.get_fps()
        self.frame = 0

        self.state = State()
        self.sanity_check()


    def calculate_table_size(self):
        return (
            2*self.table.rail_width + 2*self.table.edge_width + self.table.w,
            2*self.table.rail_width + 2*self.table.edge_width + self.table.l,
        )


    def calculate_playing_surface(self):
        return (
            self.table.w,
            self.table.l,
        )


    def sanity_check(self):
        for expected in ['L', 'R', 'T', 'B']:
            if expected not in self.table.rails:
                ValueError("ShotSimulation :: I was really expecting the table to have rails with the IDs L, R, T, B")


    def init_ball_sprites(self):
        self.ball_sprites = pygame.sprite.Group()
        for ball_id, ball in self.balls.items():
            self.ball_sprites.add(Ball(
                ball,
                self.shot.get_ball_rvw_history(ball_id),
                self.scale
            ))


    def get_fps(self):
        return 1/(self.times[-1] - self.times[-2])


    def draw_ball_tracers(self):
        if self.frame < 2:
            return

        for ball in self.ball_sprites.sprites():
            if not ball.trace:
                continue

            trace_length = self.frame if self.frame < ball.trace_length else ball.trace_length

            for n in range(trace_length - 1):
                pygame.gfxdraw.line(
                    self.screen,
                    ball.xs[self.frame - trace_length + n],
                    ball.ys[self.frame - trace_length + n],
                    ball.xs[self.frame - trace_length + n + 1],
                    ball.ys[self.frame - trace_length + n + 1],
                    (*ball.color, 255 * (1 - np.exp(-n/trace_length))),
                )


    def draw_polygon(self, coords, color):
        pygame.draw.polygon(self.screen, color, coords)


    def draw_arc(self, x, y, r, start, end, color, n=30):
        start, end = np.deg2rad(start), np.deg2rad(end)
        thetas = np.linspace(start, end, n)
        coords = [(x, y)]
        for theta in thetas:
            coords.append((x + r*np.cos(theta), y + r*np.sin(theta)))

        self.draw_polygon(coords, color)


    def draw_table(self):
        self.screen.fill(self.cloth_color)

        edge = self.px['edge']
        rail = self.px['rail']
        tx = self.px['table_x']
        ty = self.px['table_y']

        # Bottom edge
        self.draw_polygon([(edge, 0), (edge, edge), (tx-edge, edge), (tx-edge, 0)], self.edge_color)
        self.draw_polygon([(edge, edge), (edge, edge+rail), (tx-edge, edge+rail), (tx-edge, edge)], self.rail_color)

        # Left edge
        self.draw_polygon([(0, edge), (0, ty-edge), (edge, ty-edge), (edge, edge)], self.edge_color)
        self.draw_polygon([(edge, edge), (edge, ty-edge), (edge+rail, ty-edge), (edge+rail, edge)], self.rail_color)

        # Right edge
        self.draw_polygon([(tx-edge, edge), (tx-edge, ty-edge), (tx, ty-edge), (tx, edge)], self.edge_color)
        self.draw_polygon([(tx-edge-rail, edge), (tx-edge-rail, ty-edge), (tx-edge, ty-edge), (tx-edge, edge)], self.rail_color)

        # Top edge
        self.draw_polygon([(edge, ty-edge), (edge, ty), (tx-edge, ty), (tx-edge, ty-edge)], self.edge_color)
        self.draw_polygon([(edge, ty-edge-rail), (edge, ty-edge), (tx-edge, ty-edge), (tx-edge, ty-edge-rail)], self.rail_color)

        # Corners
        self.draw_arc(edge, edge, edge, 180, 270, self.edge_color)
        self.draw_arc(edge, ty-edge, edge, 90, 180, self.edge_color)
        self.draw_arc(tx-edge, ty-edge, edge, 0, 90, self.edge_color)
        self.draw_arc(tx-edge, edge, edge, 270, 360, self.edge_color)

        # Left/right diamonds
        for i in range(9):
            pygame.draw.circle(
                self.screen,
                DIAMOND_COLOR,
                (int(edge/2), int(edge/2 + (ty - edge)*i/8)),
                self.px['diamond']
            )
            pygame.draw.circle(
                self.screen,
                DIAMOND_COLOR,
                (tx-int(edge/2), int(edge/2 + (ty - edge)*i/8)),
                self.px['diamond']
            )

        # Bottom/top diamonds
        for i in range(5):
            pygame.draw.circle(
                self.screen,
                DIAMOND_COLOR,
                (int(edge/2 + (tx - edge)*i/4), int(edge/2)),
                self.px['diamond'],
            )
            pygame.draw.circle(
                self.screen,
                DIAMOND_COLOR,
                (int(edge/2 + (tx - edge)*i/4), int(ty - edge/2)),
                self.px['diamond'],
            )


    def display(self):
        # Flip vertical axis so origin is bottom left
        display_surface = pygame.display.get_surface()
        display_surface.blit(pygame.transform.flip(display_surface, False, True), dest=(0, 0))

        # Update the display
        pygame.display.flip()


    def draw_balls(self):
        # Draw the balls on the screen
        for ball in self.ball_sprites:
            self.screen.blit(ball.surf, ball.rect)


    def update_balls(self, frame):
        for ball in self.ball_sprites:
            ball.update(frame=frame)


    def handle_events(self):
        if not self.state.paused:
            self.update_balls(self.frame)
            self.frame += 1

        elif self.state.frame_backward:
            self.frame -= 1
            self.update_balls(self.frame)

        elif self.state.frame_forward:
            self.frame += 1
            self.update_balls(self.frame)

        if self.frame >= self.num_frames:
            # Restart animation
            self.frame = 0

        if self.state.decrease_speed:
            self.fps = max([1, self.fps*0.96])
        elif self.state.increase_speed:
            self.fps = min([30, self.fps*1.04])


    def start(self):
        while self.state.running:
            self.state.update()
            self.draw_table()
            self.draw_balls()
            self.draw_ball_tracers()
            self.display()
            self.handle_events()
            self.clock.tick(self.fps)


class State(object):
    def __init__(self):
        self.running = True
        self.paused = False
        self.frame_forward = False
        self.frame_backward = False
        self.increase_speed = False
        self.decrease_speed = False


    def update(self):
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: self.running = False
                elif event.key == K_SPACE: self.paused = not self.paused
                elif event.key == K_DOWN: self.decrease_speed = True
                elif event.key == K_UP: self.increase_speed = True
                elif event.key == K_RIGHT: self.paused = True; self.frame_forward = True
                elif event.key == K_LEFT: self.paused = True; self.frame_backward = True
            elif event.type == KEYUP:
                if event.key == K_DOWN: self.decrease_speed = False
                elif event.key == K_UP: self.increase_speed = False
                elif event.key == K_RIGHT: self.frame_forward = False
                elif event.key == K_LEFT: self.frame_backward = False
            elif event.type == QUIT:
                self.running = False


