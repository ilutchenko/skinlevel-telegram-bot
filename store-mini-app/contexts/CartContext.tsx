
import React, { createContext, useState, useContext, ReactNode, useMemo } from 'react';
import { Product, CartItem } from '../types';

interface CartContextType {
    cartItems: Map<number, CartItem>;
    addToCart: (product: Product) => void;
    removeFromCart: (productId: number) => void;
    updateQuantity: (productId: number, quantity: number) => void;
    clearCart: () => void;
    totalItems: number;
    totalPrice: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [cartItems, setCartItems] = useState<Map<number, CartItem>>(new Map());

    const addToCart = (product: Product) => {
        // FIX: Explicitly type prevItems to help TypeScript's type inference.
        setCartItems((prevItems: Map<number, CartItem>) => {
            const newItems = new Map(prevItems);
            const existingItem = newItems.get(product.id);
            if (existingItem) {
                newItems.set(product.id, { ...existingItem, quantity: existingItem.quantity + 1 });
            } else {
                newItems.set(product.id, { product, quantity: 1 });
            }
            return newItems;
        });
    };

    const removeFromCart = (productId: number) => {
        // FIX: Explicitly type prevItems to help TypeScript's type inference.
        setCartItems((prevItems: Map<number, CartItem>) => {
            const newItems = new Map(prevItems);
            const existingItem = newItems.get(productId);
            if (existingItem && existingItem.quantity > 1) {
                newItems.set(productId, { ...existingItem, quantity: existingItem.quantity - 1 });
            } else {
                newItems.delete(productId);
            }
            return newItems;
        });
    };
    
    const updateQuantity = (productId: number, quantity: number) => {
        // FIX: Explicitly type prevItems to help TypeScript's type inference.
        setCartItems((prevItems: Map<number, CartItem>) => {
            const newItems = new Map(prevItems);
            if (quantity <= 0) {
                 newItems.delete(productId);
            } else {
                 const existingItem = newItems.get(productId);
                 if (existingItem) {
                    newItems.set(productId, { ...existingItem, quantity });
                 }
            }
            return newItems;
        });
    }

    const clearCart = () => {
        setCartItems(new Map());
    };
    
    const { totalItems, totalPrice } = useMemo(() => {
        let itemsCount = 0;
        let priceTotal = 0;
        for (const item of cartItems.values()) {
            itemsCount += item.quantity;
            priceTotal += item.product.price * item.quantity;
        }
        return { totalItems: itemsCount, totalPrice: priceTotal };
    }, [cartItems]);

    return (
        <CartContext.Provider value={{ cartItems, addToCart, removeFromCart, updateQuantity, clearCart, totalItems, totalPrice }}>
            {children}
        </CartContext.Provider>
    );
};

export const useCart = () => {
    const context = useContext(CartContext);
    if (context === undefined) {
        throw new Error('useCart must be used within a CartProvider');
    }
    return context;
};
