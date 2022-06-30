# (C) Copyright 1996- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""
Demo tests for raw template.
"""

import unittest

import numpy as np
import scipy.stats

from PACKAGE_NAME.debias import ISIMIP


class TestISIMIPsteps(unittest.TestCase):
    def test_step6_get_P_obs_future_factsheet_edge_case(self):
        P_obs_hist = 0
        P_cm_hist = 0.8
        P_cm_future = 0.9

        P_obs_future = ISIMIP._step6_get_P_obs_future(P_obs_hist, P_cm_hist, P_cm_future)

        assert np.isclose(P_obs_future, 0.1)

    def test_step4_correct_sort_lower_threshold(self):
        debiaser = ISIMIP.from_variable("pr")
        cm_future = scipy.stats.gamma.rvs(a=1, size=1000)
        debiaser.lower_threshold = np.quantile(cm_future, 0.1)

        step4_output = debiaser.step4(cm_future)
        step4_outside_thresholds = step4_output[
            np.logical_not(debiaser._get_mask_for_values_between_thresholds(step4_output))
        ]
        cm_future_outside_bounds = cm_future[
            np.logical_not(debiaser._get_mask_for_values_between_thresholds(cm_future))
        ]

        assert all(np.argsort(step4_outside_thresholds) == np.argsort(cm_future_outside_bounds))

    def test_step4_correct_sort_bounded_variable(self):
        debiaser = ISIMIP.from_variable("rsds")
        cm_future = scipy.stats.beta.rvs(a=1, b=2, size=1000)
        debiaser.lower_threshold = np.quantile(cm_future, 0.1)
        debiaser.upper_threshold = np.quantile(cm_future, 0.9)

        step4_output = debiaser.step4(cm_future)
        step4_outside_thresholds = step4_output[
            np.logical_not(debiaser._get_mask_for_values_between_thresholds(step4_output))
        ]
        cm_future_outside_bounds = cm_future[
            np.logical_not(debiaser._get_mask_for_values_between_thresholds(cm_future))
        ]

        assert all(np.argsort(step4_outside_thresholds) == np.argsort(cm_future_outside_bounds))

    def test_step4_values_between_thresholds_unchanged(self):
        debiaser = ISIMIP.from_variable("rsds")
        cm_future = scipy.stats.beta.rvs(a=1, b=2, size=1000)
        debiaser.lower_threshold = np.quantile(cm_future, 0.1)
        debiaser.upper_threshold = np.quantile(cm_future, 0.9)

        step4_output = debiaser.step4(cm_future)
        step4_between_thresholds = debiaser._get_values_between_thresholds(step4_output)
        cm_future_between_thresholds = debiaser._get_values_between_thresholds(cm_future)

        assert all(step4_between_thresholds == cm_future_between_thresholds)


class TestISIMIPRunningWindowIteration(unittest.TestCase):
    def test__get_window_centers(self):
        debiaser = ISIMIP.from_variable("pr")
        debiaser.running_window_mode = True
        debiaser.running_window_length = 31

        for i in range(1, 30):
            debiaser.running_window_step_length = i
            window_centers = debiaser._get_window_centers(366)

            # Not day appearing only every four years in there
            assert not 366 in window_centers
            if 366 % debiaser.running_window_step_length > 0:
                # Enough window centers
                assert window_centers.size == (366 // debiaser.running_window_step_length) + 1
                # First and last window-center not drastically different
                # assert window_centers[0] - (366 - window_centers[-1]) <= 1
            else:
                # Enough window centers
                assert window_centers.size == (366 // debiaser.running_window_step_length)
            # Equally spaced: except last one: when 366 is replaced by 365
            assert all(
                window_centers[1 : (window_centers.size - 1)] - window_centers[0 : (window_centers.size - 2)]
                == debiaser.running_window_step_length
            )

    def test__get_indices_around_window_center(self):
        debiaser = ISIMIP.from_variable("pr")
        debiaser.running_window_mode = True
        debiaser.running_window_length = 31

        days_of_years = np.repeat(np.tile(1, 367), 10)
        for i in range(1, 30):
            debiaser.running_window_step_length = i
            window_centers = debiaser._get_window_centers(366)
            for center in window_centers:
                indices = debiaser._get_indices_around_window_center(days_of_years, center)
                # Check all indexes that we would expect in window are part of:
                indices_center = np.where(days_of_years == center)[0]
                window_indexes = np.concatenate(
                    [
                        np.mod(
                            np.arange(
                                index_center - debiaser.running_window_length // 2,
                                index_center + debiaser.running_window_length // 2 + 1,
                            ),
                            days_of_years.size,
                        )
                        for index_center in indices_center
                    ]
                )
                assert all(x in indices for x in window_indexes)
