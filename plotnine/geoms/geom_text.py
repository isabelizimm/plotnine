from contextlib import suppress
from warnings import warn

from matplotlib.text import Text

try:
    from adjustText import adjust_text
except ImportError:
    HAS_ADJUST_TEXT = False
else:
    HAS_ADJUST_TEXT = True

from ..exceptions import PlotnineWarning
from ..utils import to_rgba, order_as_data_mapping
from ..doctools import document
from ..positions import position_nudge
from ..exceptions import PlotnineError
from .geom import geom


# Note: hjust & vjust are parameters instead of aesthetics
# due to a limitation imposed by MPL
# see: https://github.com/matplotlib/matplotlib/pull/1181
@document
class geom_text(geom):
    """
    Textual annotations

    {usage}

    Parameters
    ----------
    {common_parameters}
    parse : bool (default: False)
        If :py:`True`, the labels will be rendered with
        `latex <http://matplotlib.org/users/usetex.html>`_.
    family : str (default: None)
        Font family.
    fontweight : int or str (default: normal)
        Font weight.
    fontstyle : str (default: normal)
        Font style. One of *normal*, *italic* or *oblique*
    nudge_x : float (default: 0)
        Horizontal adjustment to apply to the text
    nudge_y : float (default: 0)
        Vertical adjustment to apply to the text
    adjust_text: dict (default: None)
        Parameters to :class:`adjustText.adjust_text` will repel
        overlapping texts. This parameter takes priority of over
        ``nudge_x`` and ``nudge_y``.

        ``adjust_text`` does not work well when it is used in the
        first layer of the plot, or if it is the only layer.
        For more see the documentation at
        https://github.com/Phlya/adjustText/wiki .
    format_string : str (default: None)
        If not :py:`None`, then the text is formatted with this
        string using :meth:`str.format` e.g::

            # 2.348 -> "2.35%"
            geom_text(format_string="{:.2f}%")

    path_effects : list (default: None)
        If not :py:`None`, then the text will use these effects.
        See `path_effects
        <https://matplotlib.org/tutorials/advanced/patheffects_guide.html>`_
        documentation for more details.

    See Also
    --------
    plotnine.geoms.geom_label
    matplotlib.text.Text
    matplotlib.patheffects

    """
    _aesthetics_doc = """
    {aesthetics_table}

    .. rubric:: Aesthetics Descriptions

    ha
        Horizontal alignment. One of *left*, *center* or *right.*

    va
        Vertical alignment. One of *top*, *center*, *bottom*, *baseline*.

    """
    DEFAULT_AES = {'alpha': 1, 'angle': 0, 'color': 'black',
                   'size': 11, 'lineheight': 1.2, 'ha': 'center',
                   'va': 'center'}
    REQUIRED_AES = {'label', 'x', 'y'}
    DEFAULT_PARAMS = {'stat': 'identity', 'position': 'identity',
                      'na_rm': False, 'parse': False,
                      'family': None, 'fontweight': 'normal',
                      'fontstyle': 'normal', 'nudge_x': 0, 'nudge_y': 0,
                      'adjust_text': None,
                      'format_string': None,
                      'path_effects': None}

    def __init__(self, mapping=None, data=None, **kwargs):
        data, mapping = order_as_data_mapping(data, mapping)
        nudge_kwargs = {}
        adjust_text = kwargs.get('adjust_text', None)
        if adjust_text is None:
            with suppress(KeyError):
                nudge_kwargs['x'] = kwargs['nudge_x']
            with suppress(KeyError):
                nudge_kwargs['y'] = kwargs['nudge_y']
            if nudge_kwargs:
                kwargs['position'] = position_nudge(**nudge_kwargs)
        elif not HAS_ADJUST_TEXT:
            raise PlotnineError(
                "To use adjust_text you must install the adjustText "
                "package."
            )

        # Accomodate the old names
        if mapping and 'hjust' in mapping:
            mapping['ha'] = mapping.pop('hjust')

        if mapping and 'vjust' in mapping:
            mapping['va'] = mapping.pop('vjust')

        geom.__init__(self, mapping, data, **kwargs)

    def setup_data(self, data):
        parse = self.params['parse']
        fmt = self.params['format_string']

        # format
        if fmt:
            data['label'] = [fmt.format(l) for l in data['label']]

        # Parse latex
        if parse:
            data['label'] = [f'${l}$' for l in data['label']]

        return data

    def draw_panel(self, data, panel_params, coord, ax, **params):
        super().draw_panel(data, panel_params, coord, ax, **params)

    @staticmethod
    def draw_group(data, panel_params, coord, ax, **params):
        data = coord.transform(data, panel_params)

        # Bind color and alpha
        color = to_rgba(data['color'], data['alpha'])

        # Create a dataframe for the plotting data required
        # by ax.text
        df = data[['x', 'y', 'size']].copy()
        df['s'] = data['label']
        df['rotation'] = data['angle']
        df['linespacing'] = data['lineheight']
        df['color'] = color
        df['ha'] = data['ha']
        df['va'] = data['va']
        df['family'] = params['family']
        df['fontweight'] = params['fontweight']
        df['fontstyle'] = params['fontstyle']
        df['zorder'] = params['zorder']
        df['rasterized'] = params['raster']
        df['clip_on'] = True

        # 'boxstyle' indicates geom_label so we need an MPL bbox
        draw_label = 'boxstyle' in params
        if draw_label:
            fill = to_rgba(data.pop('fill'), data['alpha'])
            if isinstance(fill, tuple):
                fill = [list(fill)] * len(data['x'])
            df['facecolor'] = fill

            if params['boxstyle'] in ('round', 'round4'):
                boxstyle = '{},pad={},rounding_size={}'.format(
                    params['boxstyle'],
                    params['label_padding'],
                    params['label_r'])
            elif params['boxstyle'] in ('roundtooth', 'sawtooth'):
                boxstyle = '{},pad={},tooth_size={}'.format(
                    params['boxstyle'],
                    params['label_padding'],
                    params['tooth_size'])
            else:
                boxstyle = '{},pad={}'.format(
                    params['boxstyle'],
                    params['label_padding'])
            bbox = {'linewidth': params['label_size'],
                    'boxstyle': boxstyle}
        else:
            bbox = {}

        texts = []

        # For labels add a bbox
        for i in range(len(data)):
            kw = df.iloc[i].to_dict()
            if draw_label:
                kw['bbox'] = bbox
                kw['bbox']['edgecolor'] = params['boxcolor'] or kw['color']
                kw['bbox']['facecolor'] = kw.pop('facecolor')
            text_elem = ax.text(**kw)
            texts.append(text_elem)
            if params['path_effects']:
                text_elem.set_path_effects(params['path_effects'])

        _adjust = params['adjust_text']
        if _adjust:
            if params['zorder'] == 1:
                warn(
                    "For better results with adjust_text, it should "
                    "not be the first layer or the only layer.",
                    PlotnineWarning
                )

            arrowprops = _adjust.pop('arrowprops', {})
            if 'color' not in arrowprops:
                arrowprops['color'] = color[0]

            adjust_text(
                texts,
                ax=ax,
                arrowprops=arrowprops,
                **_adjust
            )

    @staticmethod
    def draw_legend(data, da, lyr):
        """
        Draw letter 'a' in the box

        Parameters
        ----------
        data : dataframe
            Legend data
        da : DrawingArea
            Canvas
        lyr : layer
            Layer

        Returns
        -------
        out : DrawingArea
        """
        key = Text(x=0.5*da.width,
                   y=0.5*da.height,
                   text='a',
                   alpha=data['alpha'],
                   size=data['size'],
                   family=lyr.geom.params['family'],
                   color=data['color'],
                   rotation=data['angle'],
                   horizontalalignment='center',
                   verticalalignment='center')
        da.add_artist(key)
        return da
