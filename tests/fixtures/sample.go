// Package demo.
package demo

import "fmt"

// Add adds two numbers.
func Add(a int, b int) int {
	// inner comment
	return a + b
}

type Point struct {
	X int
	Y int
}

func (p Point) Sum() int {
	return p.X + p.Y
}

func Guarded(err error) error {
	if err != nil {
		return fmt.Errorf("wrapped: %w", err)
	}
	return nil
}
