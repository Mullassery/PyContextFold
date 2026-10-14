//! Crate-level docs.

use std::collections::HashMap;

/// Doc comment on a function.
pub fn add(a: i32, b: i32) -> i32 {
    // inner comment
    let sum = a + b;
    sum
}

pub struct Point {
    pub x: i32,
    pub y: i32,
}

impl Point {
    /// Construct a point.
    pub fn new(x: i32, y: i32) -> Self {
        Point { x, y }
    }

    pub fn length(&self) -> f64 {
        ((self.x * self.x + self.y * self.y) as f64).sqrt()
    }
}

pub fn guarded(map: &HashMap<String, i32>) -> i32 {
    match map.get("k") {
        Some(v) => *v,
        None => 0,
    }
}
