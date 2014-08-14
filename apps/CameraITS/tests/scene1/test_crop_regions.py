# Copyright 2014 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import its.image
import its.device
import its.objects
import its.target
import pylab
import os.path
import matplotlib
import matplotlib.pyplot
import copy
import numpy

def main():
    """Test that crop regions work.
    """
    NAME = os.path.basename(__file__).split(".")[0]

    # A list of 5 regions, specified in normalized (x,y,w,h) coords.
    # The regions correspond to: TL, TR, BL, BR, CENT
    REGIONS = [(0.0, 0.0, 0.5, 0.5),
               (0.5, 0.0, 0.5, 0.5),
               (0.0, 0.5, 0.5, 0.5),
               (0.5, 0.5, 0.5, 0.5),
               (0.25, 0.25, 0.5, 0.5)]

    with its.device.ItsSession() as cam:
        props = cam.get_camera_properties()
        a = props['android.sensor.info.activeArraySize']
        ax, ay = a["left"], a["top"]
        aw, ah = a["right"] - a["left"], a["bottom"] - a["top"]
        e, s = its.target.get_target_exposure_combos(cam)["minSensitivity"]
        print "Active sensor region (%d,%d %dx%d)" % (ax, ay, aw, ah)

        # Capture a full frame.
        req = its.objects.manual_capture_request(s,e)
        cap_full = cam.do_capture(req)
        img_full = its.image.convert_capture_to_rgb_image(cap_full)
        its.image.write_image(img_full, "%s_full.jpg" % (NAME))
        wfull, hfull = cap_full["width"], cap_full["height"]

        # Capture a burst of crop region frames.
        # Each is captured into an image 1/2x1/2 the size, which should allow
        # these crop images to be compared with 1/2x1/2 regions that are
        # cropped from the full frame.
        reqs = []
        for x,y,w,h in REGIONS:
            req = its.objects.manual_capture_request(s,e)
            req["android.scaler.cropRegion"] = {
                    "top": int(ay + ah * y),
                    "left": int(ax + aw * x),
                    "right": int(ax + aw * (x + w)),
                    "bottom": int(ay + ah * (y + h))}
            reqs.append(req)
        fmt = {"format":"yuv", "width":wfull/2, "height":hfull/2}
        caps_regions = cam.do_capture(reqs, fmt)
        match_failed = False
        for i,cap in enumerate(caps_regions):
            a = cap["metadata"]["android.scaler.cropRegion"]
            ax, ay = a["left"], a["top"]
            aw, ah = a["right"] - a["left"], a["bottom"] - a["top"]

            # Match this crop image against each of the five regions of
            # the full image, to find the best match (which should be
            # the region that corresponds to this crop image).
            img_crop = its.image.convert_capture_to_rgb_image(cap)
            its.image.write_image(img_crop, "%s_crop%d.jpg" % (NAME, i))
            min_diff = None
            min_diff_region = None
            for j,(x,y,w,h) in enumerate(REGIONS):
                tile_full = its.image.get_image_patch(img_full, x,y,w,h)
                wtest = min(tile_full.shape[1], aw)
                htest = min(tile_full.shape[0], ah)
                tile_full = tile_full[0:htest:, 0:wtest:, ::]
                tile_crop = img_crop[0:htest:, 0:wtest:, ::]
                its.image.write_image(tile_full, "%s_fullregion%d.jpg"%(NAME,j))
                diff = numpy.fabs(tile_full - tile_crop).mean()
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    min_diff_region = j
            if i != min_diff_region:
                match_failed = True
            print "Crop image %d (%d,%d %dx%d) best match with region %d"%(
                    i, ax, ay, aw, ah, min_diff_region)

        assert(not match_failed)

if __name__ == '__main__':
    main()

