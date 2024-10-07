# ------------------------------------------------------------------------------
# Copyright (c) Acoular Development Team.
# ------------------------------------------------------------------------------

import acoular as ac
import numpy as np
import pytest

PRECISION_MAPPING = {
    ('64', 'real'): 'float64',
    ('32', 'real'): 'float32',
    ('64', 'complex'): 'complex128',
    ('32', 'complex'): 'complex64',
}


class TestInOutBase:
    def create_time_data(self, numsamples, sample_freq=64):
        return ac.TimeSamples(
            data=ac.WNoiseGenerator(
                sample_freq=sample_freq,
                numsamples=numsamples,
            ).signal()[:, np.newaxis],
            sample_freq=sample_freq,
        )

    def create_source(self, numsamples, sample_freq=64):
        return self.create_time_data(numsamples=numsamples, sample_freq=sample_freq)

    @pytest.mark.parametrize('numsamples', [1, 64, 127, 128, 129, 256])
    def test_numsamples(self, numsamples):
        source = self.create_source(numsamples=numsamples)
        res = ac.tools.return_result(source, num=128)
        assert res.shape[0] == source.numsamples


class TestRFFT(TestInOutBase):
    def create_source(self, numsamples, sample_freq=64, block_size=64, window='Rectangular'):
        ts = self.create_time_data(numsamples=numsamples, sample_freq=sample_freq)
        return ac.RFFT(source=ts, block_size=block_size, window=window)

    @pytest.mark.parametrize('numsamples', [64, 127, 128, 129, 256])
    def test_numsamples(self, numsamples):
        source = self.create_source(numsamples=numsamples, block_size=64)
        res = ac.tools.return_result(source, num=128)
        assert res.shape[0] == source.numsamples

    def test_reflect_source_changes(self):
        fft = self.create_source(numsamples=8, block_size=64)
        digest = fft.digest
        freqs = fft.freqs
        # change source sample_freq
        fft.source.sample_freq *= 2
        assert fft.digest != digest
        assert not np.array_equal(fft.freqs, freqs)

    def test_digest_changes(self):
        fft = self.create_source(numsamples=8, block_size=64)
        digest = fft.digest
        fft.scaling = 'energy'
        assert fft.digest != digest
        digest = fft.digest
        fft.precision = 'complex64'
        assert fft.digest != digest
        digest = fft.digest
        fft.block_size = 16
        assert fft.digest != digest
        digest = fft.digest
        fft.window = 'Hanning'
        assert fft.digest != digest
        digest = fft.digest
        fft.overlap = '50%'
        assert fft.digest != digest
        digest = fft.digest

    @pytest.mark.parametrize('window', ['Rectangular', 'Hanning', 'Hamming', 'Blackman', 'Bartlett'])
    def test_equal_power(self, window):
        block_size = 128
        num = 2
        fft = self.create_source(numsamples=block_size * 2, block_size=block_size, window=window)
        ap = ac.AutoPowerSpectra(source=fft)
        cp = ac.CrossPowerSpectra(source=fft)
        ps = ac.PowerSpectra(source=fft.source, cached=False, block_size=block_size, window=window)
        ap_data = next(ap.result(num))
        cp_data = next(cp.result(num))
        np.testing.assert_allclose(ap_data, cp_data)
        np.testing.assert_allclose(ap_data.mean(axis=0).reshape(-1), ps.csm[:, :, :].reshape(-1))

    @pytest.mark.parametrize('precision', ['64', '32'])
    def test_precision(self, precision):
        """
        test if the desired precision is reflected in the output
        """
        fft = self.create_source(numsamples=8, block_size=8)
        fft.precision = PRECISION_MAPPING[(precision, 'complex')]
        data = next(fft.result(1))
        assert data.dtype == PRECISION_MAPPING[(precision, 'complex')]


class TestIRFFT(TestInOutBase):
    def create_source(self, numsamples, sample_freq=64, block_size=64, window='Rectangular', precision='64'):
        ts = self.create_time_data(numsamples=numsamples, sample_freq=sample_freq)
        return ac.IRFFT(
            source=ac.RFFT(
                source=ts, block_size=block_size, window=window, precision=PRECISION_MAPPING[(precision, 'complex')]
            ),
            precision=PRECISION_MAPPING[(precision, 'real')],
        )

    @pytest.mark.parametrize('numsamples', [64, 127, 128, 129, 256])
    def test_numsamples(self, numsamples):
        source = self.create_source(numsamples=numsamples, block_size=64)
        res = ac.tools.return_result(source, num=128)
        assert res.shape[0] == source.numsamples

    @pytest.mark.parametrize('num', [8, 16])
    def test_equal_fft_ifft(self, num):
        source = self.create_source(numsamples=num, block_size=8)
        data = next(source.source.source.result(num))  # TimeSamples output block
        data_comp = next(source.result(num))
        np.testing.assert_allclose(data, data_comp)

    @pytest.mark.parametrize('num', [1, 4, 7, 8, 9, 16])
    def test_irfft_buffer(self, num):
        ifft = self.create_source(numsamples=64, block_size=8)
        data = ac.tools.return_result(ifft.source.source, num=num)
        data_comp = ac.tools.return_result(ifft, num=num)
        np.testing.assert_allclose(data, data_comp)

    @pytest.mark.parametrize('precision', ['64', '32'])
    def test_precision(self, precision):
        """
        test if the desired precision is reflected in the output
        """
        ifft = self.create_source(numsamples=64, precision=precision)
        data = next(ifft.result(1))
        assert data.dtype == PRECISION_MAPPING[(precision, 'real')]


class TestAutoPowerSpectra(TestInOutBase):
    def create_source(self, numsamples, sample_freq=64, block_size=64, window='Rectangular', precision='64'):
        ts = self.create_time_data(numsamples=numsamples, sample_freq=sample_freq)
        return ac.AutoPowerSpectra(
            source=ac.RFFT(
                source=ts, block_size=block_size, window=window, precision=PRECISION_MAPPING[(precision, 'complex')]
            ),
            precision=PRECISION_MAPPING[(precision, 'real')],
        )

    @pytest.mark.parametrize('numsamples', [64, 127, 128, 129, 256])
    def test_numsamples(self, numsamples):
        source = self.create_source(numsamples=numsamples, block_size=64)
        res = ac.tools.return_result(source, num=128)
        assert res.shape[0] == source.numsamples

    @pytest.mark.parametrize('precision', ['64', '32'])
    def test_precision(self, precision):
        """
        test if the desired precision is reflected in the output
        """
        ap = self.create_source(numsamples=64, precision=precision)
        data = next(ap.result(1))
        assert data.dtype == PRECISION_MAPPING[(precision, 'real')]


class TestCrossPowerSpectra(TestAutoPowerSpectra):
    def create_source(self, numsamples, sample_freq=64, block_size=64, window='Rectangular', precision='64'):
        ts = self.create_time_data(numsamples=numsamples, sample_freq=sample_freq)
        return ac.CrossPowerSpectra(
            source=ac.RFFT(
                source=ts, block_size=block_size, window=window, precision=PRECISION_MAPPING[(precision, 'complex')]
            ),
            precision=PRECISION_MAPPING[(precision, 'complex')],
        )

    @pytest.mark.parametrize('precision', ['64', '32'])
    def test_precision(self, precision):
        """
        test if the desired precision is reflected in the output
        """
        cp = self.create_source(numsamples=64, precision=precision)
        data = next(cp.result(1))
        assert data.dtype == PRECISION_MAPPING[(precision, 'complex')]
