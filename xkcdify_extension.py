#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2025 Gui Meira
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
Makes paths squiggly in a style similar to XKCD comics.
Optionally replaces text fonts with Humor Sans.
"""

import math
import random
import inkex
from inkex import bezier, CubicSuperPath

######################################
# Font replacement
######################################
#The font replacement code was adapted from the Replace Font extension that comes with Inkscape
svg_text_tag = '{http://www.w3.org/2000/svg}text'
text_tags = [
    svg_text_tag,
    '{http://www.w3.org/2000/svg}tspan',
    '{http://www.w3.org/2000/svg}flowRoot',
    '{http://www.w3.org/2000/svg}flowPara',
    '{http://www.w3.org/2000/svg}flowSpan',
]
font_attributes = ['font-family', '-inkscape-font-specification']
font_name = 'Humor Sans'

def has_font_style_attrs(node):
    return node.tag in text_tags and "style" in node.attrib

def replace_font(node):
    #If the node does not have a style element, create an empty one:
    if not node.style:
        node.style = {}
    
    if node.tag == svg_text_tag:
        for attr in font_attributes:
            node.style[attr] = font_name
        return
    
    for attr in font_attributes:
        if attr in node.style:
            del node.style[attr]

def recursive_replace_font(nodes):
    for e in find_recursive(nodes, has_font_style_attrs):
        replace_font(e)


######################################
# Sketch
######################################
#The sketch algorithm is based on the one used in matplotlib's xkcd function
#https://github.com/matplotlib/matplotlib/blob/96c9a3049477715f9dd21c6a945b3f2006ebad4e/src/path_converters.h#L995-L1104
#The logic for subdividing the paths is based on the Add Nodes extension that comes with Inkscape
def is_path_element(node):
    return isinstance(node, inkex.PathElement)

def sketch(node, max_length, scale, length, randomness, prng):
    log_randomness = 2.0*math.log(randomness)
    p_scale = (2*math.pi)/(length*randomness)
    #Transform the path into a sequence of cubic beziers and split each curve into small parts:
    new_path = []

    #For each list of points in the superpath:
    for c in node.path.to_superpath():
        #Append first point of the path to the new path
        new_path.append([c[0][:]])

        #For all the other points in this path:
        for i in range(1, len(c)):
            #Calculate length of the bezier from the last point of new_path to the point we're currently processing:
            curve_length = bezier.cspseglength(new_path[-1][-1], c[i])

            #Compute number of splits such that all segments of this curve are shorter than max_length:
            splits = math.ceil(curve_length/max_length)

            #For each of the segments we need to calculate:
            for s in range(int(splits), 1, -1):
                segment = bezier.cspbezsplitatlength(new_path[-1][-1], c[i], 1.0/s)
                mutable_segment = [[list(e) for e in elements] for elements in segment]
                new_path[-1][-1] = mutable_segment[0]
                next_pt = mutable_segment[1]
                c[i] = mutable_segment[2]
                new_path[-1].append(next_pt[:])
            new_path[-1].append(c[i])

        #Path splitting is done, now we apply the noise:
        p = 0.0
        last_x = new_path[-1][0][1][0]
        last_y = new_path[-1][0][1][1]

        for i in range(1, len(new_path[-1])-1):
            rand = prng.random()
            p += math.exp(rand*log_randomness)
            den = last_x - new_path[-1][i][1][0]
            num = last_y - new_path[-1][i][1][1]
            last_x = new_path[-1][i][1][0]
            last_y = new_path[-1][i][1][1]
            hyp = num*num + den*den
            
            if hyp != 0:
                hyp = math.sqrt(hyp)
                r = math.sin(p*p_scale)*scale
                r_over_hyp = r/hyp
                dx = r_over_hyp*num
                dy = r_over_hyp*den
                
                for pt in new_path[-1][i]:
                    pt[0] += dx
                    pt[1] -= dy

    node.path = CubicSuperPath(new_path).to_path(curves_only=False)

def recursive_sketch(nodes, max_length, scale, length, randomness, prng):
    for e in find_recursive(nodes, is_path_element):
        sketch(e, max_length, scale, length, randomness, prng)


######################################
# Utils
######################################
def find_recursive(elements, filter):
    for e in elements:
        if filter(e):
            yield e
        
        #Search the children of this element:
        for c in find_recursive(e, filter):
            yield c


######################################
# Extension
######################################
class XKCDifyExtension(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--replace_font", type=inkex.Boolean)
        pars.add_argument("--max_segment_length", type=float)
        pars.add_argument("--max_segment_length_unit", type=str)
        pars.add_argument("--p_scale", type=float)
        pars.add_argument("--p_length", type=float)
        pars.add_argument("--p_randomness", type=float)
        pars.add_argument("--random_seed", type=int)
        pars.add_argument("--tab", type=str) #unused

    def effect(self):
        #Replace fonts if the user requested it:
        if self.options.replace_font:
            recursive_replace_font(self.svg.selection)
        
        #Make lines squiggly:
        max_segment_length = self.svg.viewport_to_unit(f"{self.options.max_segment_length}{self.options.max_segment_length_unit}")
        scale = self.options.p_scale
        length = self.options.p_length
        randomness = self.options.p_randomness
        prng = random.Random(self.options.random_seed)
        recursive_sketch(self.svg.selection, max_segment_length, scale, length, randomness, prng)

if __name__ == '__main__':
    XKCDifyExtension().run()
