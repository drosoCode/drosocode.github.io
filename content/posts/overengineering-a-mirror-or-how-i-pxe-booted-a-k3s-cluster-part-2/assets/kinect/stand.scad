difference() {
    translate([166,-64,-0.32])
        import("kinect_stand.stl");

    translate([-19,0,0])
        cube([19,112,19]);
}

tv_depth = 30;
clamp_size = 6;
translate([-tv_depth-clamp_size,0,0]) {
    color("blue")
    cube([tv_depth+clamp_size,112,4]);

    color("red")
    cube([clamp_size,112,16]);
}