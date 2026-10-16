# v3-style names used by ARnet_sub, mapped onto h3-py v4
import h3 as _h3
h3_to_geo = _h3.cell_to_latlng
get_res0_indexes = _h3.get_res0_cells
h3_to_children = _h3.cell_to_children
geo_to_h3 = _h3.latlng_to_cell
uncompact = lambda cells, res: _h3.uncompact_cells(cells, res)
