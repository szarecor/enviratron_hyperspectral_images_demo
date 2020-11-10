import datetime
from fnmatch import fnmatch


class EnviratronFileNameParser:
    """ A helper class for deciphering the metadata stored in the Enviratron project output files. """

    def __init__(self, filename):

        self.raw_filepath = filename
        self.type = None

        path_list = self.raw_filepath.split("/")
        filename = path_list[-1]
        filename_without_extension, extension = filename.rsplit(".", 1)
        filename_list = filename_without_extension.split("_")

        self.raw_filename = filename
        self.file_extension = extension

        # ints_list will be used to construct a datetime and also extract the subject plant's ordinal/id from the filename string:
        self._ints_list = [int(i) for i in filter(self._only_ints_filter, filename_list)]
        self.parse_ordinal()
        self.parse_chamber_id(path_list)
        self.parse_datetime()
        self.parse_file_type()
        # And attempt to extract the pixel height from the filename:
        self.parse_physical_dimensions()

    def parse_ordinal(self, filename_ints_list=None):
        """ Attempts to extract the image/plant ordinal/index from the filename string. The ordinal/index is the value
        immmediately before the 4-digit year in the filename string.

        Example scenarios:
            Pull "2" from "hsr_m_0_d_rp_2_2018_8_17_9_40_58_63_f_30_w_1024_h_56.bin"
            Pull "7" from thermo_pose_7_2018_8_10_9_0_34_883.yml
        """
        if filename_ints_list is None:
            if self._ints_list:
                ints_list = self._ints_list
            else:
                filename_list = self.raw_filename.split(".", 1)[0].split("_")
                ints_list = [
                    int(i) for i in filter(self._only_ints_filter, filename_list)
                ]

        # one version of the hyperspectral reference file naming convention requires special care:
        if fnmatch(self.raw_filename, "hsr_*.*"):
            try:
                self.ordinal = ints_list[1]
            except IndexError:
                pass
        else:
            try:
                self.ordinal = ints_list[0]
            except IndexError:
                pass

    def parse_physical_dimensions(self, filename_list=None):
        """ Attempts to extract physical dimensions (width, height and sometimes bands) from a filename string.

        Given a filename like hsr_m_0_w_rp_0_2018_8_17_9_45_26_509_f_30_w_1024_h_56.bin:
         the "f_30" denotes a pixel height of 30
         the "w_1024" denotes a pixel width of 1024
         and the "h_56" denotes 56 spectral bands
        """

        if filename_list is None:
            filename_list = self.raw_filename.split(".", 1)[0].split("_")

        # Height:
        try:
            # Find the index of the last "f" in the list and then get the next element in the list:
            # Please Note: This gets the index of the element that follows "f" and not the index for "f" itself
            height_index = len(filename_list) - filename_list[::-1].index("f")
            self.height = int(filename_list[height_index])
        except ValueError:
            # These filetypes don't have physical dimension info in their filenames, but are known/static, so we can hardcode:
            if fnmatch(self.raw_filename, "thermo_*.jpg"):
                self.height = 480
            elif fnmatch(self.raw_filename, "thermo_*.bin"):
                self.height = 480
            elif fnmatch(self.raw_filename, "rgb_*.jpg"):
                self.height = 1303

        # Width:
        try:
            # As with height, get the index for the list element following the last "w":
            width_index = len(filename_list) - filename_list[::-1].index("w")
            self.width = int(filename_list[width_index])

        except ValueError:
            if fnmatch(self.raw_filename, "thermo_*.jpg"):
                self.width = 640
            elif fnmatch(self.raw_filename, "thermo_*.bin"):
                self.width = 640
            elif fnmatch(self.raw_filename, "rgb_*.jpg"):
                self.width = 156

        # Hyperspectral Bands:
        if fnmatch(self.raw_filename, "hs*.bin") or fnmatch(
            self.raw_filename, "hs_*.npy"
        ):
            try:
                self.bands = int(filename_list[filename_list.index("h") + 1])
            except ValueError:
                self.bands = 56

        # Special case
        if fnmatch(self.raw_filename, "*_hs_r*.bin"):
            try:
                bands_index = len(filename_list) - filename_list[::-1].index("h")
                self.bands = int(filename_list[bands_index])
            except IndexError:
                self.bands = 56


    def parse_chamber_id(self, path_list=None):
        """ Tries to extract a chamber id from the path. This data is not in the actual filename, but in the fullpath

        An example path looks like /Volumes/Data/enviratron_imaging/35_clean/chamber_5/c1_2018_8_10_8_56_49_389/thermo_pose_12_2018_8_10_9_3_23_608.yml
        where "chamber_5" denotes the chamber_id and this method should return the integer value "5".

        """
        if path_list is None:
            path_list = self.raw_filepath.split("/")

        chamber_list = [s for s in path_list if "chamber_" in s]

        if len(chamber_list) > 0:
            self.chamber_id = int(chamber_list[0].split("_")[-1])
        else:
            self.chamber_id = None

    def _only_ints_filter(self, string):
        """ Filters a list based on the ability to successfully call int() on each member of the list """
        try:
            int(string)
            return True
        except ValueError:
            return False

    def parse_datetime(self):
        """ Tries to extract the datetime information from a filename string. Should fail silently when unsuccessful.

        Given the example filename 'thermo_pose_12_2018_8_10_9_3_23_608.yml', The datetime data is contained in '2018_8_10_9_3_23_608'
        Most files adhere to the above convention, but there is also 'hsr_m_0_d_rp_2_2018_8_17_9_40_58_63_f_30_w_1024_h_56.bin'

        """
        self.datetime = None
        self.year = None
        self.month = None
        self.day = None
        self.hour = None
        self.minute = None
        self.seconds = None

        # One variation of the hyperspectral reference file naming convention requires pruning
        # to normalize it to the more common convention:
        if fnmatch(self.raw_filename, "hsr_*.*"):
            ints_list = self._ints_list[1:]
        else:
            ints_list = self._ints_list

        try:
            _datetime = datetime.datetime(
                ints_list[1],
                ints_list[2],
                ints_list[3],
                ints_list[4],
                ints_list[5],
                ints_list[6],
            )

            self.datetime = _datetime.isoformat()
            self.year = _datetime.year
            self.month = _datetime.month
            self.day = _datetime.day
            self.hour = _datetime.hour
            self.minute = _datetime.minute
            self.second = _datetime.second

        except ValueError:
            pass
        except IndexError:
            pass

    def parse_file_type(self):
        """ Derives a human-readable string filetype descriptor from the filename. """

        filename = self.raw_filename.split("/")[-1]

        # Matching patterns for fnmatch() and the corresponding string descriptors. The order is important!
        filename_to_type_mapping = (
            ("*.pcd", "point cloud"),
            ("rgb_pose*.yml", "rgb pose"),
            ("rgb*.jpg", "rgb image"),
            ("PAM*.yml", "fluorometer pam"),
            ("ir_*.bin", "infrared"),
            ("depth_*.bin", "depth"),
            ("depth_pose_*.yml", "depth pose"),
            # Hyperspectral reference filenaming conventions have changed, so account for both formats:
            ("?_hs_rd_*.bin", "hyperspectral reference dark"),
            ("hsr_*_d_rp_*.bin", "hyperspectral reference dark"),
            ("?_hs_rw_*.bin", "hyperspectral reference white"),
            ("hsr_*_w_rp_*.bin", "hyperspectral reference white"),
            ("hs_*.bin", "hyperspectral"),
            ("?_hs_*_pose.csv", "hyperspectral pose"),
            ("hsr_*_pose.csv", "hyperspectral reference pose"),
            ("hsr_*.csv", "hyperspectral csv"),
            ("?_hs_*.csv", "hyperspectral csv"),
            ("thermo_pose_*.yml", "thermal pose"),
            ("thermo_*.bin", "thermal"),
            ("thermo_*.jpg", "thermal image"),
        )

        file_type = None

        for file_type_tuple in filename_to_type_mapping:
            match = fnmatch(filename, file_type_tuple[0])
            if match is True:
                file_type = file_type_tuple[1]
                break

        self.type = file_type

    def as_dict(self):
        # Returns a simple dict of the class instance's values
        data = {k: v for k, v in self.__dict__.items()}
        return data


if __name__ == "__test__":

    pass
