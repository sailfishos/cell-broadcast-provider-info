Name:       cell-broadcast-provider-info
Summary:    Cell broadcast emergency alert channel database
Version:    20260511
Release:    1
License:    ASL 2.0
BuildArch:  noarch
URL:        https://github.com/sailfishos/cell-broadcast-provider-info/
Source0:    %{name}-%{version}.tar.bz2

BuildRequires:  gstreamer1.0-plugins-base
BuildRequires:  gstreamer1.0-tools
BuildRequires:  python3-base
BuildRequires:  pkgconfig(Qt5Core)

%description
This package contains informational files describing public warning cell
broadcast channels used by emergency alert systems in different countries.

The package contains only lookup data so consumers can be updated without
moving the telephony runtime or user interface packages.

%package devel
Summary:    Development files for %{name}
Requires:   %{name} = %{version}-%{release}

%description devel
Contains development files for %{name}.

%changelog
* Wed May 13 2026 Jolla Ltd. <info@jolla.com> - 20260511-1
- Initial Sailfish OS cell broadcast provider info package.

%prep
%setup -q -n %{name}-%{version}

%build
%qmake5

%install
%qmake5_install

%files
%license LICENSE
%doc README.md
%{_datadir}/cell-broadcast-provider-info

%files devel
%{_datadir}/pkgconfig/cell-broadcast-provider-info.pc
