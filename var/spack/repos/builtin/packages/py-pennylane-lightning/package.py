# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)


from spack.package import *


class PyPennylaneLightning(CMakePackage, PythonExtension):
    """The PennyLane-Lightning plugin provides a fast state-vector simulator written in C++."""

    homepage = "https://docs.pennylane.ai/projects/lightning"
    git = "https://github.com/PennyLaneAI/pennylane-lightning.git"
    url = "https://github.com/PennyLaneAI/pennylane-lightning/archive/refs/tags/v0.28.2.tar.gz"
    tag = "v0.28.2"

    maintainers("mlxd", "AmintorDusko")

    version("master", branch="master")
    version("0.28.2", sha256="c9b3afed0585681ccaf4df09fb12f2b7f09a8a1ba97a9b979139fe4a24509f31")
    version(
        "0.28.0",
        sha256="f5849c2affb5fb57aca20feb40ca829d171b07db2304fde0a37c2332c5b09e18",
        deprecated=True,
    )  # on Spack v0.19.0

    patch(
        "v0.28-spack_support.patch",
        when="@0.28.2",
        sha256="26e79a0a01fbd1d9364d2328ccdbdcdd5109ea289a4e79f86f7a8206bcb35419",
    )

    variant("blas", default=True, description="Build with BLAS support")
    variant(
        "dispatcher",
        default=True,
        description="Build with AVX2/AVX512 gate automatic dispatching support",
    )
    variant("kokkos", default=True, description="Build with Kokkos support")
    variant("openmp", default=True, description="Build with OpenMP support")

    variant("native", default=False, description="Build natively for given hardware")
    variant("verbose", default=False, description="Build with full verbosity")

    variant("cpptests", default=False, description="Build CPP tests")
    variant("cppbenchmarks", default=False, description="Build CPP benchmark examples")

    variant(
        "build_type",
        default="Release",
        description="CMake build type",
        values=("Debug", "Release", "RelWithDebInfo", "MinSizeRel"),
    )

    extends("python")

    # hard dependencies
    depends_on("cmake@3.21:3.24,3.25.2:", type="build")
    depends_on("ninja", type=("run", "build"))

    # variant defined dependencies
    depends_on("blas", when="+blas")
    depends_on("kokkos@3.7.00", when="+kokkos")
    depends_on("kokkos-kernels@3.7.00", when="+kokkos")
    depends_on("llvm-openmp", when="+openmp %apple-clang")

    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-pybind11", type=("build"))
    depends_on("py-pip", type="build")
    depends_on("py-wheel", type="build")


class CMakeBuilder(spack.build_systems.cmake.CMakeBuilder):
    build_directory = "build"

    def cmake_args(self):
        """
        Here we specify all variant options that can be dynamicaly specified at build time
        """
        args = [
            self.define_from_variant("CMAKE_BUILD_TYPE", "build_type"),
            self.define_from_variant("ENABLE_OPENMP", "openmp"),
            self.define_from_variant("ENABLE_NATIVE", "native"),
            self.define_from_variant("ENABLE_BLAS", "blas"),
            self.define_from_variant("CMAKE_VERBOSE_MAKEFILE:BOOL", "verbose"),
            self.define_from_variant("BUILD_TESTS", "cpptests"),
            self.define_from_variant("BUILD_BENCHMARKS", "cppbenchmarks"),
            self.define_from_variant("ENABLE_GATE_DISPATCHER", "dispatcher"),
        ]

        if self.spec.variants["kokkos"].value:
            args += [
                "-DENABLE_KOKKOS=ON",
                f"-DKokkos_Core_DIR={self.spec['kokkos'].home}",
                f"-DKokkos_Kernels_DIR={self.spec['kokkos-kernels'].home}",
            ]
        else:
            args += ["-DENABLE_KOKKOS=OFF"]

        return args

    def build(self, pkg, spec, prefix):
        super().build(pkg, spec, prefix)
        cm_args = ";".join(
            [
                s[2:]
                for s in self.cmake_args()
                if s[2:] not in ["BUILD_TESTS:BOOL=ON", "BUILD_BENCHMARKS:BOOL=ON"]
            ]
        )
        args = ["-i", f"--define={cm_args}"]
        build_ext = Executable(f"{self.spec['python'].command.path}" + " setup.py build_ext")
        build_ext(*args)

    def install(self, pkg, spec, prefix):
        pip_args = std_pip_args + ["--prefix=" + prefix, "."]
        pip(*pip_args)
        super().install(pkg, spec, prefix)

    @run_after("install")
    @on_package_attributes(run_tests=True)
    def test_lightning_build(self):
        with working_dir(self.stage.source_path):
            pl_runner = Executable(
                join_path(self.prefix, "bin", "pennylane_lightning_test_runner")
            )
            pl_runner()
