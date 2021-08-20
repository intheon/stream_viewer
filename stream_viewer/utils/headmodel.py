#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from pathlib import Path
import numpy as np
import os
import warnings


def parse_headmodel_file(filename):
    from scipy.io.matlab import loadmat
    from scipy.sparse import csc_matrix
    filepath = Path(filename)
    if not filepath.exists():
        filepath = Path(os.path.expanduser('~')) / '.stream_viewer' / 'headmodel' / filepath.name
    HM = loadmat(filepath, squeeze_me=True)
    leadfield = HM['leadfield']['matrix'][()]
    sensors = dict()
    sensors['labels'] = HM['sensors']['labels'][()]
    sensors['coordinates'] = HM['sensors']['coordinates'][()]
    laplacian = csc_matrix(HM['laplacian']['matrix'][()])

    meshes = [{'name': _, 'vertices': HM['meshes']['vertices'][ix], 'faces': HM['meshes']['faces'][ix] - 1}
              for ix, _ in enumerate(HM['meshes']['name'])]

    if HM['atlases'].size == 1:
        atlases = [{_: HM['atlases'][_][()] for _ in HM['atlases'].dtype.names}]
        atlases[0]['labeling'] -= 1
    else:
        atlases = [{'name': _, 'labeling': HM['atlases']['labeling'][ix] - 1, 'labels': HM['atlases']['labels'][ix]}
                   for ix, _ in enumerate(HM['atlases']['name'])]

    for atl in atlases:
        if atl['name'] == 'Desikan–Killiany' and len(atl['labeling']) == 4495:
            _labels = atl['labels'].tolist()

            atl['labeling'][202] = _labels.index('lingual L.1')  # From 'lingual R.2'
            switch_lr = [248, 334, 343, 1415, 1503, 1568, 1607, 1657, 1820, 1848, 2520, 2605, 3145, 3189, 3429, 3465,
                         3499, 3531, 3639, 3689, 3788, 3796, 3870, 3914, 3957, 4029, 4109, 4173, 4333]
            for v_id in switch_lr:
                old_roi_spl = _labels[atl['labeling'][v_id]].split(' ')
                new_roi = old_roi_spl[0] + ' ' + ('L' if old_roi_spl[1][0] == 'R' else 'R') + old_roi_spl[1][1:]
                atl['labeling'][v_id] = _labels.index(new_roi)

            # Previously known mislabels
            atl['labeling'][1038] = _labels.index('superiortemporal L.3')  # From middletemporal L.4
            atl['labeling'][985] = _labels.index('superiortemporal L.3')  # From supramarginal L.10
            atl['labeling'][1161] = _labels.index('superiortemporal L.4')  # From middletemporal L.6
            atl['labeling'][1509] = _labels.index('superiortemporal L.6')  # From precentral L.9
            atl['labeling'][1361] = _labels.index('superiortemporal L.5')  # From precentral L.9

    coords = HM['meta']['coordinates'][()]
    meta = {'coordinates': {_: coords[_][()] for _ in coords.dtype.names},
            'system': 'MNI'}
    del HM
    return {'leadfield': leadfield, 'sensors': sensors, 'laplacian': laplacian,
            'meshes': meshes, 'atlases': atlases, 'meta': meta}


def internalize_coordinates(coords, unit, x, y, z):
    """Convert the given coordinates (Nx3 array) into a unified
    internal coordinate system.

    The internal system is as follows:
    * unit=meters
    * x=right
    * y=front
    * z=up

    Args:
        coords: Nx3 array of coordinates to convert
        unit: the unit of the coordinates, e.g., 'meters', 'millimeters',
          can also be 'guess'
        x: orientation of the X axis relative to the head, e.g., 'front'
        y: orientation of the Y axis relative to the head, e.g., 'left'
        z: orientation of the Z axis relative to the head, e.g., 'up'

    Returns:
        coords: the transformed coordinates
    """

    # unit conversion
    if unit.lower() == 'guess':
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            max_coord = np.nanmax(np.abs(coords[:, :2]))
        if not np.isnan(max_coord):
            if max_coord < 0.1:
                unit = 'meters'
            elif max_coord < 1:
                unit = 'centimeters'
            elif max_coord < 10:
                unit = 'millimeters'

    if unit.lower() in ['millimeters', 'mm']:
        coords /= 1000.0
    elif unit.lower() in ['centimeters', 'cm']:
        coords /= 100.0
    elif not unit.lower() in ['meters', 'guess']:
        raise RuntimeError("Unsupported unit: %s" % unit)

    # rotations, etc
    if x == 'front' and y == 'left' and z == 'up':
        # +X nose direction
        # rotate 90 degrees clockwise (looking down on head)
        coords = np.dot(coords, np.array([[0, 1, 0],
                                          [-1, 0, 0],
                                          [0, 0, 1]]))
    elif x == 'back' and y == 'right' and z == 'up':
        # -X nose direction
        coords = np.dot(coords, np.array([[0, -1, 0],
                                          [1, 0, 0],
                                          [0, 0, 1]]))
    elif not (x == 'right' and y == 'front' and z == 'up'):
        # not +Y nose direction
        raise RuntimeError("Unsupported coordinate system (%s,%s,%s)" % (x, y,
                                                                         z))
    return coords