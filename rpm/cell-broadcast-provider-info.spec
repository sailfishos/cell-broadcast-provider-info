Name:       cell-broadcast-provider-info
Summary:    Cell broadcast emergency alert channel database
Version:    20260511
Release:    1
License:    ASL 2.0
BuildArch:  noarch
URL:        https://github.com/sailfishos/cell-broadcast-provider-info/
Source0:    %{name}-%{version}.tar.bz2

BuildRequires:  gstreamer1.0-plugins-base
BuildRequires:  gstreamer1.0-plugins-good
BuildRequires:  gstreamer1.0-tools
BuildRequires:  python3-base

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

%prep
%setup -q -n %{name}-%{version}

%install
install -D -m 0644 data/channels.json \
    %{buildroot}%{_datadir}/cell-broadcast-provider-info/channels.json

python3 tools/generate-cellbroadcast-attention-tones.py \
    --output-dir %{buildroot}%{_datadir}/cell-broadcast-provider-info/attention-tones

install -D -m 0644 cell-broadcast-provider-info.pc \
    %{buildroot}%{_datadir}/pkgconfig/cell-broadcast-provider-info.pc

%files
%license LICENSE
%{_datadir}/cell-broadcast-provider-info

%files devel
%{_datadir}/pkgconfig/cell-broadcast-provider-info.pc
