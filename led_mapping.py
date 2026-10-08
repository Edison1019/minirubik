"""Cube geometry used to derive the small renderer mapping tables."""
FACES = ['U', 'L', 'F', 'R', 'B', 'D']
CORNERS = [
    ('U', 'R', 'F'), ('D', 'F', 'R'), ('D', 'L', 'F'),
    ('U', 'B', 'R'), ('D', 'R', 'B'), ('D', 'B', 'L'),
    ('U', 'L', 'B'), ('U', 'F', 'L'),
]
COORDS = [(1,1,1), (1,-1,1), (-1,-1,1), (1,1,-1),
          (1,-1,-1), (-1,-1,-1), (-1,1,-1), (-1,1,1)]
SLOTS = [(1,0), (0,1), (1,1), (2,1), (3,1), (1,2)]


def facelet(corner, face):
    x, y, z = COORDS[corner]
    row, col = {'F': (y < 0, x > 0), 'B': (y < 0, x < 0),
                'R': (y < 0, z < 0), 'L': (y < 0, z > 0),
                'U': (z > 0, x > 0), 'D': (z < 0, x > 0)}[face]
    return FACES.index(face)*4 + int(row)*2 + int(col)


HOME_COLORS = [FACES.index(face) for faces in CORNERS for face in faces]
DEST_FACELETS = [facelet(i, face) for i, faces in enumerate(CORNERS) for face in faces]
PIXELS = [(SLOTS[f][0]*9+col*4, 2+SLOTS[f][1]*7+row*3)
          for f in range(6) for row in range(2) for col in range(2)]
